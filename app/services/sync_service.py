import logging
import asyncio
from uuid import UUID
from fastapi import BackgroundTasks

from app.domain.entities import SyncJob, SyncResult
from app.domain.enums import SyncStatus
from app.infrastructure.automation.web.fiorilli_browser import FiorilliBrowser
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, repo: SqlAlchemyRepo):
        self.repo = repo

    async def create_job(self, triggered_by: str = "api") -> SyncJob:
        job = SyncJob(triggered_by=triggered_by)
        await self.repo.save_job(job)
        return job

    async def get_job(self, job_id: UUID) -> SyncJob:
        return await self.repo.get_job(job_id)

    async def list_jobs(self) -> list[SyncJob]:
        return await self.repo.list_jobs()

    async def run_sync_background(self, job_id: UUID):
        job = await self.repo.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for execution")
            return

        await self.repo.update_job_status(job_id, SyncStatus.RUNNING)
        logger.info(f"Started background sync for job {job_id}")

        try:
            # Run blocking Fiorilli sync in a thread pool to avoid blocking the event loop
            result = await asyncio.to_thread(self._execute_sync_logic, job_id)
            
            status = SyncStatus.SUCCESS if result.success else SyncStatus.FAILED
            await self.repo.update_job_status(job_id, status, result.message)
            logger.info(f"Job {job_id} finished with status {status}")

        except Exception as e:
            logger.exception(f"Unhandled error in job {job_id}")
            await self.repo.update_job_status(job_id, SyncStatus.FAILED, str(e))

    def _execute_sync_logic(self, job_id: UUID) -> SyncResult:
        # Note: In a real app, we might want to inject the browser instance or use a factory
        browser = FiorilliBrowser()
        try:
            browser.download_employees()
            browser.download_leaves()
            return SyncResult(success=True, status=SyncStatus.SUCCESS, message="Fiorilli sync completed")
        except Exception as e:
            logger.error(f"Fiorilli sync failed: {e}")
            return SyncResult(success=False, status=SyncStatus.FAILED, message=str(e))
        finally:
            browser.close_driver()
