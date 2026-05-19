import asyncio
import logging

from app.core.database import async_session_factory
from app.core.settings import settings
from app.domain.enums import SyncStatus
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.services.credential_crypto import extract_credentials_from_metadata
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


class RetryScheduler:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"Retry Scheduler started (interval: {self.interval_seconds}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Retry Scheduler stopped")

    async def _run(self):
        while self._running:
            try:
                await self._check_and_retry_jobs()
            except Exception as e:
                logger.error(f"Error in Retry Scheduler: {e}")

            await asyncio.sleep(self.interval_seconds)

    async def _check_and_retry_jobs(self):
        async with async_session_factory() as session:
            repo = SqlAlchemyRepo(session)
            ready_jobs = await repo.get_jobs_ready_for_retry()

            if not ready_jobs:
                return

            logger.info(f"Found {len(ready_jobs)} jobs ready for retry")

            for job in ready_jobs:
                logger.info(
                    f"Scheduling retry for job {job.id} (Attempt {job.retry_count + 1})"
                )

                creds = extract_credentials_from_metadata(job.metadata)
                if creds is None:
                    logger.warning(
                        f"Job {job.id} has no stored credentials; marking FAILED."
                    )
                    await repo.update_job_status(
                        job.id,
                        SyncStatus.FAILED,
                        "No stored credentials available for retry",
                    )
                    continue

                fiorilli_password, ahgora_password = creds

                asyncio.create_task(
                    SyncService.run_sync_task_standalone(
                        job.id,
                        settings.FIORILLI_URL,
                        settings.FIORILLI_USER,
                        fiorilli_password,
                        settings.AHGORA_URL,
                        settings.AHGORA_USER,
                        settings.AHGORA_COMPANY,
                        ahgora_password,
                    )
                )


scheduler = RetryScheduler()
