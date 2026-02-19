from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import SyncJob, SyncLog, SyncStatus, AutomationTask, AutomationTaskType, AutomationTaskStatus
from app.infrastructure.db.models import SyncJobModel, SyncLogModel, AutomationTaskModel


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
                metadata_info=job.metadata,
                retry_count=job.retry_count,
                next_retry_at=job.next_retry_at,
            )
            self.session.add(db_job)
        else:
            db_job.status = job.status
            db_job.started_at = job.started_at
            db_job.finished_at = job.finished_at
            db_job.error_message = job.error_message
            db_job.metadata_info = job.metadata
            db_job.retry_count = job.retry_count
            db_job.next_retry_at = job.next_retry_at

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
            metadata=db_job.metadata_info,
            retry_count=db_job.retry_count,
            next_retry_at=db_job.next_retry_at,
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
                metadata=db.metadata_info,
                retry_count=db.retry_count,
                next_retry_at=db.next_retry_at,
            )
            for db in db_jobs
        ]

    async def update_job_status(
        self, job_id: UUID, status: SyncStatus, message: Optional[str] = None
    ):
        db_job = await self.session.get(SyncJobModel, job_id)
        if db_job:
            db_job.status = status
            if status == SyncStatus.RUNNING:
                db_job.started_at = datetime.now()
                # Clear next_retry_at when starting
                db_job.next_retry_at = None
            elif status in [SyncStatus.SUCCESS, SyncStatus.FAILED, SyncStatus.CANCELLED]:
                db_job.finished_at = datetime.now()

            if message:
                db_job.error_message = message

            await self.session.commit()

    async def increment_job_retry(self, job_id: UUID, next_retry_at: datetime):
        db_job = await self.session.get(SyncJobModel, job_id)
        if db_job:
            db_job.retry_count += 1
            db_job.next_retry_at = next_retry_at
            db_job.status = SyncStatus.RETRYING
            await self.session.commit()

    async def get_jobs_ready_for_retry(self) -> List[SyncJob]:
        now = datetime.now()
        result = await self.session.execute(
            select(SyncJobModel)
            .where(SyncJobModel.status == SyncStatus.RETRYING)
            .where(SyncJobModel.next_retry_at <= now)
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
                metadata=db.metadata_info,
                retry_count=db.retry_count,
                next_retry_at=db.next_retry_at,
            )
            for db in db_jobs
        ]

    async def add_log(self, job_id: UUID, level: str, message: str) -> None:
        db_log = SyncLogModel(
            job_id=job_id, level=level, message=message, timestamp=datetime.now()
        )
        self.session.add(db_log)
        await self.session.commit()

    async def get_job_logs(self, job_id: UUID) -> List[SyncLog]:
        result = await self.session.execute(
            select(SyncLogModel)
            .filter_by(job_id=job_id)
            .order_by(SyncLogModel.timestamp.asc())
        )
        db_logs = result.scalars().all()
        return [
            SyncLog(
                id=db.id,
                job_id=db.job_id,
                level=db.level,
                message=db.message,
                timestamp=db.timestamp,
            )
            for db in db_logs
        ]

    async def save_automation_task(self, task: AutomationTask) -> None:
        db_task = await self.session.get(AutomationTaskModel, task.id)
        if not db_task:
            db_task = AutomationTaskModel(
                id=task.id,
                job_id=task.job_id,
                type=task.type,
                status=task.status,
                payload_info=task.payload,
                created_at=task.created_at,
                started_at=task.started_at,
                finished_at=task.finished_at,
                error_message=task.error_message,
                retry_count=task.retry_count,
            )
            self.session.add(db_task)
        else:
            db_task.status = task.status
            db_task.payload_info = task.payload
            db_task.started_at = task.started_at
            db_task.finished_at = task.finished_at
            db_task.error_message = task.error_message
            db_task.retry_count = task.retry_count

        await self.session.commit()

    async def get_automation_tasks_by_job(self, job_id: UUID) -> List[AutomationTask]:
        result = await self.session.execute(
            select(AutomationTaskModel)
            .filter_by(job_id=job_id)
            .order_by(AutomationTaskModel.created_at.asc())
        )
        db_tasks = result.scalars().all()
        return [
            AutomationTask(
                id=db.id,
                job_id=db.job_id,
                type=db.type,
                status=db.status,
                payload=db.payload_info,
                created_at=db.created_at,
                started_at=db.started_at,
                finished_at=db.finished_at,
                error_message=db.error_message,
                retry_count=db.retry_count,
            )
            for db in db_tasks
        ]
    async def get_all_automation_tasks(
        self, status: Optional[AutomationTaskStatus] = None
    ) -> List[AutomationTask]:
        query = select(AutomationTaskModel).order_by(AutomationTaskModel.created_at.desc())
        if status:
            query = query.filter_by(status=status)

        result = await self.session.execute(query)
        db_tasks = result.scalars().all()
        return [
            AutomationTask(
                id=db.id,
                job_id=db.job_id,
                type=db.type,
                status=db.status,
                payload=db.payload_info,
                created_at=db.created_at,
                started_at=db.started_at,
                finished_at=db.finished_at,
                error_message=db.error_message,
                retry_count=db.retry_count,
            )
            for db in db_tasks
        ]
