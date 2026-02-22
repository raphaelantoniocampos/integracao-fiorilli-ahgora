from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import (
    SyncJob,
    SyncLog,
    SyncStatus,
    AutomationTask,
    AutomationTaskStatus,
)
import pandas as pd
from app.infrastructure.db.models import (
    SyncJobModel,
    SyncLogModel,
    AutomationTaskModel,
    AhgoraEmployeeModel,
    AhgoraLeaveModel,
)


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
            db_job.started_at = job.started_at  # type: ignore
            db_job.finished_at = job.finished_at  # type: ignore
            db_job.error_message = job.error_message  # type: ignore
            db_job.metadata_info = job.metadata
            db_job.retry_count = job.retry_count
            db_job.next_retry_at = job.next_retry_at  # type: ignore

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

    async def get_job_status(self, job_id: UUID) -> Optional[SyncStatus]:
        job = await self.get_job(job_id)

        return job.status if job else None

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
                db_job.next_retry_at = None  # type: ignore
            elif status in [
                SyncStatus.SUCCESS,
                SyncStatus.FAILED,
                SyncStatus.CANCELLED,
            ]:
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

    async def add_log(
        self, job_id: UUID, level: str, message: str, task_id: Optional[UUID] = None
    ) -> None:
        db_log = SyncLogModel(
            job_id=job_id,
            task_id=task_id,
            level=level,
            message=message,
            timestamp=datetime.now(),
        )
        self.session.add(db_log)
        await self.session.commit()

    async def get_job_logs(self, job_id: UUID) -> List[SyncLog]:
        result = await self.session.execute(
            select(SyncLogModel)
            .filter_by(job_id=job_id, task_id=None)
            .order_by(SyncLogModel.timestamp.asc())
        )
        db_logs = result.scalars().all()
        return [
            SyncLog(
                id=db.id,
                job_id=db.job_id,
                task_id=db.task_id,
                level=db.level,
                message=db.message,
                timestamp=db.timestamp,
            )
            for db in db_logs
        ]

    async def get_task_logs(self, task_id: UUID) -> List[SyncLog]:
        result = await self.session.execute(
            select(SyncLogModel)
            .filter_by(task_id=task_id)
            .order_by(SyncLogModel.timestamp.asc())
        )
        db_logs = result.scalars().all()
        return [
            SyncLog(
                id=db.id,
                job_id=db.job_id,
                task_id=db.task_id,
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
            db_task.started_at = task.started_at  # type: ignore
            db_task.finished_at = task.finished_at  # type: ignore
            db_task.error_message = task.error_message  # type: ignore
            db_task.retry_count = task.retry_count

        await self.session.commit()

    async def get_task(self, task_id: UUID) -> Optional[AutomationTask]:
        db_task = await self.session.get(AutomationTaskModel, task_id)
        if not db_task:
            return None

        return AutomationTask(
            id=db_task.id,
            job_id=db_task.job_id,
            type=db_task.type,
            status=db_task.status,
            payload=db_task.payload_info,
            created_at=db_task.created_at,
            started_at=db_task.started_at,
            finished_at=db_task.finished_at,
            error_message=db_task.error_message,
            retry_count=db_task.retry_count,
        )

    async def update_task_status(
        self, task_id: UUID, status: AutomationTaskStatus, message: Optional[str] = None
    ):
        db_task = await self.session.get(AutomationTaskModel, task_id)
        if db_task:
            db_task.status = status
            if status == AutomationTaskStatus.RUNNING:
                db_task.started_at = datetime.now()
            elif status in [
                AutomationTaskStatus.SUCCESS,
                AutomationTaskStatus.FAILED,
                AutomationTaskStatus.CANCELLED,
            ]:
                db_task.finished_at = datetime.now()

            if message:
                db_task.error_message = message

            await self.session.commit()

    async def save_automation_tasks_batch(self, tasks: List[AutomationTask]) -> None:
        db_tasks = [
            AutomationTaskModel(
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
            for task in tasks
        ]
        self.session.add_all(db_tasks)
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
        query = select(AutomationTaskModel).order_by(
            AutomationTaskModel.created_at.desc()
        )
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

    async def get_ahgora_employees_df(self) -> pd.DataFrame:
        """Returns the cached Ahgora employees as a DataFrame"""
        result = await self.session.execute(select(AhgoraEmployeeModel))
        employees = result.scalars().all()
        data = [
            {
                "id": emp.id,
                "name": emp.name,
                "position": emp.position,
                "scale": emp.scale,
                "department": emp.department,
                "location": emp.location,
                "admission_date": emp.admission_date,
                "dismissal_date": emp.dismissal_date,
            }
            for emp in employees
        ]
        return pd.DataFrame(data)

    async def get_ahgora_leaves_df(self) -> pd.DataFrame:
        """Returns the cached Ahgora leaves as a DataFrame"""
        result = await self.session.execute(select(AhgoraLeaveModel))
        leaves = result.scalars().all()
        data = [
            {
                "id": leave.employee_id,
                "cod": leave.cod,
                "cod_name": leave.cod_name,
                "start_date": leave.start_date,
                "end_date": leave.end_date,
                "start_time": leave.start_time,
                "end_time": leave.end_time,
                "duration": leave.duration,
            }
            for leave in leaves
        ]
        return pd.DataFrame(data)

    async def save_ahgora_employees_batch(self, employees: List[dict]) -> None:
        """Performs a merge (upsert) for a batch of Ahgora employees"""
        for emp_dict in employees:
            db_emp = AhgoraEmployeeModel(
                id=emp_dict.get("id"),
                name=emp_dict.get("name"),
                position=emp_dict.get("position"),
                scale=emp_dict.get("scale"),
                department=emp_dict.get("department"),
                location=emp_dict.get("location"),
                admission_date=emp_dict.get("admission_date"),
                dismissal_date=emp_dict.get("dismissal_date"),
                last_synced_at=datetime.now(),
            )
            await self.session.merge(db_emp)
        await self.session.commit()

    async def save_ahgora_leaves_batch(self, leaves: List[dict]) -> None:
        """Saves a batch of Ahgora leaves to the DB cache"""
        for leave_dict in leaves:
            db_leave = AhgoraLeaveModel(
                employee_id=leave_dict.get(
                    "id"
                ),  # DataFrame uses 'id' for the employee id
                cod=leave_dict.get("cod"),
                cod_name=leave_dict.get("cod_name"),
                start_date=leave_dict.get("start_date"),
                end_date=leave_dict.get("end_date"),
                start_time=leave_dict.get("start_time"),
                end_time=leave_dict.get("end_time"),
                duration=leave_dict.get("duration"),
                last_synced_at=datetime.now(),
            )
            self.session.add(db_leave)
        await self.session.commit()
