from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from app.core.config import settings
from app.domain.entities import SyncJob, SyncResult, SyncLog
from app.domain.enums import SyncStatus
from app.infrastructure.automation.web.fiorilli_browser import FiorilliBrowser
from app.infrastructure.automation.web.ahgora_browser import AhgoraBrowser
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.task_registry import task_registry

logger = logging.getLogger(__name__)


class SyncService:
    MAX_JOB_RETRIES = 3

    def __init__(self, repo: SqlAlchemyRepo):
        self.repo = repo
        self._db_lock = asyncio.Lock()

    @staticmethod
    async def run_sync_task_standalone(job_id: UUID):
        """
        Static method to run a sync task with its own database session.
        This is used for background tasks to avoid session closure issues.
        """
        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            repo = SqlAlchemyRepo(session)
            service = SyncService(repo)
            await service.run_sync_background(job_id)

    async def create_job(self, triggered_by: str = "api") -> SyncJob:
        job = SyncJob(triggered_by=triggered_by)
        async with self._db_lock:
            await self.repo.save_job(job)
        return job

    async def get_job(self, job_id: UUID) -> SyncJob:
        return await self.repo.get_job(job_id)

    async def list_jobs(self) -> list[SyncJob]:
        return await self.repo.list_jobs()

    async def get_job_logs(self, job_id: UUID) -> list[SyncLog]:
        return await self.repo.get_job_logs(job_id)

    async def run_sync_background(self, job_id: UUID):
        job = await self.repo.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for execution")
            return

        async with self._db_lock:
            await self.repo.update_job_status(job_id, SyncStatus.RUNNING)
        await self._log(job_id, "INFO", f"Started background sync for job {job_id}")

        # Register the current task
        current_task = asyncio.current_task()
        task_registry.register(job_id, current_task)

        try:
            # Execute sync logic (now properly async and handles its own threading)
            result = await self._execute_sync_logic(job_id)

            if result.success:
                async with self._db_lock:
                    await self.repo.update_job_status(job_id, SyncStatus.SUCCESS, result.message)
                await self._log(
                    job_id,
                    "INFO",
                    f"Job {job_id} finished successfully: {result.message}",
                )
            else:
                # If it failed, check if we should retry (job level)
                await self._handle_job_retry(job, error_msg=result.message)

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            try:
                async with self._db_lock:
                    await self.repo.update_job_status(
                        job_id, SyncStatus.CANCELLED, "Job was cancelled by user"
                    )
                await self._log(job_id, "WARNING", "Job was cancelled")
            except Exception as e:
                logger.error(f"Failed to update status for cancelled job {job_id}: {e}")
            raise  # Re-raise to finalize task cancellation

        except Exception as e:
            logger.exception(f"Unhandled error in job {job_id}")
            # Ensure status is UPDATED even if something very bad happens
            try:
                # Handle retry even for unhandled errors
                await self._handle_job_retry(job, error_msg=str(e))
            except Exception as inner_e:
                logger.error(f"Failed to handle retry for job {job_id}: {inner_e}")
        finally:
            task_registry.unregister(job_id)

    async def _handle_job_retry(
        self, job: SyncJob, error_msg: Optional[str] = None
    ):
        """Calculates next retry and updates job if retries are available."""
        if job.retry_count >= self.MAX_JOB_RETRIES:
            final_msg = error_msg or "Max retries reached"
            async with self._db_lock:
                await self.repo.update_job_status(job.id, SyncStatus.FAILED, final_msg)
            await self._log(job.id, "ERROR", f"Sync failed permanently: {final_msg}")
            return

        # Exponential backoff: 5m, 30m, 2h
        backoffs = [
            timedelta(minutes=5),
            timedelta(minutes=30),
            timedelta(hours=2),
        ]

        delay = backoffs[job.retry_count]  # current retry_count is 0..2
        next_retry = datetime.now() + delay

        await self.repo.increment_job_retry(job.id, next_retry)
        await self._log(
            job.id,
            "WARNING",
            f"Job failed. Scaled retry {job.retry_count + 1}/{self.MAX_JOB_RETRIES} scheduled for {next_retry}",
        )

    async def kill_job(self, job_id: UUID) -> bool:
        """Cancels a running job and updates its status to CANCELLED."""
        task = task_registry.get_task(job_id)
        if not task:
            logger.warning(f"Attempted to kill non-existent or completed job {job_id}")
            return False

        logger.info(f"Request to kill job {job_id} received")

        # We update the status BEFORE cancelling so it's guaranteed recorded
        async with self._db_lock:
            await self.repo.update_job_status(
                job_id, SyncStatus.CANCELLED, "Termination requested by user"
            )

        task.cancel()
        return True

    async def kill_all_jobs(self) -> int:
        """Cancels all active sync jobs."""
        tasks = task_registry.get_all_tasks()
        count = 0
        for job_id in tasks.keys():
            if await self.kill_job(job_id):
                count += 1
        return count

    async def _log(self, job_id: UUID, level: str, message: str):
        # Log to standard logging
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"Job {job_id}: {message}")

        # Persist to DB
        async with self._db_lock:
            await self.repo.add_log(job_id, level, message)

    async def _execute_sync_logic(self, job_id: UUID) -> SyncResult:
        async def run_download_task_with_retries(
            browser_class, method_name, description, max_retries=3
        ):
            last_error = None
            for attempt in range(1, max_retries + 1):
                await self._log(
                    job_id,
                    "INFO",
                    f"Starting {description} (Attempt {attempt}/{max_retries})",
                )

                def blocking_wrapper():
                    browser = browser_class()
                    try:
                        getattr(browser, method_name)()
                    finally:
                        browser.close_driver()

                try:
                    await asyncio.to_thread(blocking_wrapper)
                    await self._log(
                        job_id, "INFO", f"Completed {description} on attempt {attempt}"
                    )
                    return True  # Success
                except Exception as e:
                    last_error = e
                    await self._log(
                        job_id,
                        "WARNING",
                        f"Attempt {attempt}/{max_retries} for {description} failed: {str(e)}",
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(2)  # Short wait before retry

            await self._log(
                job_id,
                "ERROR",
                f"All {max_retries} attempts failed for {description}: {str(last_error)}",
            )
            raise last_error

        try:
            if settings.HEADLESS_MODE:
                await self._log(
                    job_id, "INFO", "Running tasks concurrently (Headless Mode)"
                )
                await asyncio.gather(
                    run_download_task_with_retries(
                        FiorilliBrowser,
                        "download_employees",
                        "Fiorilli employees download",
                    ),
                    run_download_task_with_retries(
                        FiorilliBrowser, "download_leaves", "Fiorilli leaves download"
                    ),
                    run_download_task_with_retries(
                        AhgoraBrowser, "download_employees", "Ahgora employees download"
                    ),
                )
            else:
                await self._log(job_id, "INFO", "Running tasks sequentially (UI Mode)")
                await run_download_task_with_retries(
                    FiorilliBrowser, "download_employees", "Fiorilli employees download"
                )
                await run_download_task_with_retries(
                    FiorilliBrowser, "download_leaves", "Fiorilli leaves download"
                )
                await run_download_task_with_retries(
                    AhgoraBrowser, "download_employees", "Ahgora employees download"
                )

            # TODO: Integrate DataManager.analyze() logic here

            return SyncResult(
                success=True,
                status=SyncStatus.SUCCESS,
                message="Sync completed (Fiorilli & Ahgora)",
            )
        except Exception as e:
            logger.error(f"Sync failed after retries: {e}")
            return SyncResult(
                success=False,
                status=SyncStatus.FAILED,
                message=f"Sync failed: {str(e)}",
            )
