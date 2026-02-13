from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import SyncJob, SyncStatus
from app.infrastructure.db.models import SyncJobModel, SyncLogModel

class SqlAlchemyRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_job(self, job: SyncJob) -> None:
        # Check if job exists
        db_job = await self.session.get(SyncJobModel, job.id)
        if not db_job:
            db_job = SyncJobModel(
                id=job.id,
                status=job.status,
                triggered_by=job.triggered_by,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
                error_message=job.error_message,
                metadata_info=job.metadata
            )
            self.session.add(db_job)
        else:
            db_job.status = job.status
            db_job.started_at = job.started_at
            db_job.finished_at = job.finished_at
            db_job.error_message = job.error_message
            db_job.metadata_info = job.metadata
        
        await self.session.commit()

    async def get_job(self, job_id: UUID) -> Optional[SyncJob]:
        db_job = await self.session.get(SyncJobModel, job_id)
        if not db_job:
            return None
        
        return SyncJob(
            id=db_job.id,
            status=db_job.status,
            triggered_by=db_job.triggered_by,
            created_at=db_job.created_at,
            started_at=db_job.started_at,
            finished_at=db_job.finished_at,
            error_message=db_job.error_message,
            metadata=db_job.metadata_info
        )

    async def list_jobs(self) -> List[SyncJob]:
        result = await self.session.execute(
            select(SyncJobModel).order_by(SyncJobModel.created_at.desc())
        )
        db_jobs = result.scalars().all()
        
        return [
            SyncJob(
                id=db.id,
                status=db.status,
                triggered_by=db.triggered_by,
                created_at=db.created_at,
                started_at=db.started_at,
                finished_at=db.finished_at,
                error_message=db.error_message,
                metadata=db.metadata_info
            ) for db in db_jobs
        ]

    async def update_job_status(self, job_id: UUID, status: SyncStatus, message: Optional[str] = None):
        db_job = await self.session.get(SyncJobModel, job_id)
        if db_job:
            db_job.status = status
            if status == SyncStatus.RUNNING:
                db_job.started_at = datetime.now()
            elif status in [SyncStatus.SUCCESS, SyncStatus.FAILED]:
                db_job.finished_at = datetime.now()
            
            if message:
                db_job.error_message = message
            
            await self.session.commit()
