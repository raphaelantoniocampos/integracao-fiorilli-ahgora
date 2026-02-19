from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import SyncJob, SyncLog, AutomationTask
from app.domain.enums import AutomationTaskStatus
from app.services.sync_service import SyncService
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.database import get_db
from app.core.task_registry import task_registry

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)


@router.post(
    "/run",
    response_model=SyncJob,
    summary="Trigger Sync Job",
    description="Starts a background job to download data from Fiorilli and Ahgora and perform analysis.",
)
async def run_sync_job(
    background_tasks: BackgroundTasks, service: SyncService = Depends(get_service)
):
    job = await service.create_job(triggered_by="api")
    background_tasks.add_task(SyncService.run_sync_task_standalone, job.id)
    return job


@router.get(
    "/jobs",
    response_model=list[SyncJob],
    summary="List Sync Jobs",
    description="Returns a list of all historical and current synchronization jobs.",
)
async def list_jobs(service: SyncService = Depends(get_service)):
    return await service.list_jobs()


@router.post(
    "/jobs/{job_id}/kill",
    summary="Kill specific Sync Job",
    description="Sends a cancellation signal to a running sync job.",
)
async def kill_job(job_id: UUID, service: SyncService = Depends(get_service)):
    success = await service.kill_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not running")
    return {"message": f"Kill signal sent to job {job_id}"}


@router.post(
    "/kill-all",
    summary="Kill all active jobs",
    description="Stops every currently running synchronization job.",
)
async def kill_all_jobs(service: SyncService = Depends(get_service)):
    count = await service.kill_all_jobs()
    return {"message": f"Kill signal sent to {count} active jobs"}


@router.get(
    "/jobs/{job_id}/logs",
    response_model=list[SyncLog],
    summary="Get Job Logs",
    description="Returns all log entries associated with a specific sync job execution.",
)
async def get_job_logs(job_id: UUID, service: SyncService = Depends(get_service)):
    return await service.get_job_logs(job_id)


@router.get(
    "/jobs/{job_id}/tasks",
    response_model=list[AutomationTask],
    tags=["Automation Tasks"],
    summary="Get Job Automation Tasks",
    description="Retrieves specific tasks (Add/Remove Employee, etc.) identified during a specific sync job.",
)
async def get_automation_tasks(
    job_id: UUID, service: SyncService = Depends(get_service)
):
    return await service.get_automation_tasks(job_id)


@router.get(
    "/tasks",
    response_model=list[AutomationTask],
    tags=["Automation Tasks"],
    summary="List all Automation Tasks",
    description="Returns a global list of automation tasks identified across all jobs, with optional status filter.",
)
async def list_automation_tasks(
    status: Optional[AutomationTaskStatus] = None,
    service: SyncService = Depends(get_service),
):
    return await service.list_automation_tasks(status)


@router.get(
    "/diagnostics/registry",
    summary="Get Task Registry Diagnostics",
    description="Returns the current state of the in-memory task registry for debugging purposes.",
    tags=["Diagnostics"],
)
async def get_registry_diagnostics():
    active_tasks = task_registry.get_all_tasks()
    return {
        "active_task_count": len(active_tasks),
        "job_ids": list(active_tasks.keys()),
    }
