import logging
import asyncio
from uuid import UUID

from app.domain.entities import SyncJob, SyncResult, SyncLog
from app.domain.enums import SyncStatus
from app.infrastructure.automation.web.fiorilli_browser import FiorilliBrowser
from app.infrastructure.automation.web.ahgora_browser import AhgoraBrowser
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo

logger = logging.getLogger(__name__)


class SyncService:
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

        try:
            # Execute sync logic (now properly async and handles its own threading)
            result = await self._execute_sync_logic(job_id)

            status = SyncStatus.SUCCESS if result.success else SyncStatus.FAILED
            async with self._db_lock:
                await self.repo.update_job_status(job_id, status, result.message)
            await self._log(
                job_id,
                "INFO" if result.success else "ERROR",
                f"Job {job_id} finished with status {status}: {result.message}",
            )

        except Exception as e:
            logger.exception(f"Unhandled error in job {job_id}")
            async with self._db_lock:
                await self.repo.update_job_status(job_id, SyncStatus.FAILED, str(e))
            await self._log(job_id, "ERROR", f"Unhandled error: {str(e)}")

    async def _log(self, job_id: UUID, level: str, message: str):
        # Log to standard logging
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"Job {job_id}: {message}")

        # Persist to DB
        async with self._db_lock:
            await self.repo.add_log(job_id, level, message)

    async def _execute_sync_logic(self, job_id: UUID) -> SyncResult:
        async def run_download_task(browser_class, method_name, description):
            def blocking_wrapper():
                browser = browser_class()
                try:
                    getattr(browser, method_name)()
                finally:
                    browser.close_driver()

            await self._log(job_id, "INFO", f"Starting {description}")
            try:
                await asyncio.to_thread(blocking_wrapper)
                await self._log(job_id, "INFO", f"Completed {description}")
            except Exception as e:
                await self._log(job_id, "ERROR", f"Failed {description}: {str(e)}")
                raise e

        try:
            await asyncio.gather(
                run_download_task(
                    FiorilliBrowser, "download_employees", "Fiorilli employees download"
                ),
                run_download_task(
                    FiorilliBrowser, "download_leaves", "Fiorilli leaves download"
                ),
                run_download_task(
                    AhgoraBrowser, "download_employees", "Ahgora employees download"
                ),
            )

            # TODO: Integrate DataManager.analyze() logic here

            return SyncResult(
                success=True,
                status=SyncStatus.SUCCESS,
                message="Sync completed (Fiorilli & Ahgora)",
            )
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return SyncResult(success=False, status=SyncStatus.FAILED, message=str(e))
