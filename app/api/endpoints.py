from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import SyncJob, SyncLog, AutomationTask
from app.domain.enums import AutomationTaskStatus
from app.services.sync_service import SyncService
from app.services.task_execution_service import TaskExecutionService
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


def get_execution_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return TaskExecutionService(repo=repo)


@router.post(
    "/tasks/batch/execute",
    summary="Execute Batch Automation Tasks",
    description="Manually triggers the batch execution of specific task types for a job.",
    tags=["Automation Tasks"],
)
async def execute_batch_tasks(
    job_id: UUID,
    task_type: str,
    background_tasks: BackgroundTasks,
    service: TaskExecutionService = Depends(get_execution_service),
):
    # Execute batch in background
    background_tasks.add_task(service.execute_batch, job_id, task_type)
    return {"message": f"Batch task execution triggered for {task_type}"}


@router.post(
    "/tasks/batch/cancel",
    summary="Cancel Batch Automation Tasks",
    description="Cancels pending or running batch execution of specific task types for a job.",
    tags=["Automation Tasks"],
)
async def cancel_batch_tasks(
    job_id: UUID,
    task_type: str,
    service: TaskExecutionService = Depends(get_execution_service),
):
    await service.cancel_batch(job_id, task_type)
    return {"message": f"Batch tasks cancelled for {task_type}"}


@router.post(
    "/tasks/{task_id}/execute",
    summary="Execute Automation Task",
    description="Manually triggers the execution of a specific automation task via Selenium in the background.",
    tags=["Automation Tasks"],
)
async def execute_task(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    service: TaskExecutionService = Depends(get_execution_service),
):
    # Execute in background to prevent blocking the API response since Selenium is slow
    background_tasks.add_task(service.execute_task, task_id)
    return {"message": "Task execution triggered", "task_id": str(task_id)}


@router.post(
    "/tasks/{task_id}/cancel",
    summary="Cancel Automation Task",
    description="Manually checks and cancels an individual running or pending task.",
    tags=["Automation Tasks"],
)
async def cancel_task(
    task_id: UUID,
    service: TaskExecutionService = Depends(get_execution_service),
):
    success = await service.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível cancelar a tarefa. Ou ela não existe ou já foi finalizada/cancelada.",
        )
    return {"message": "Tarefa cancelada com sucesso"}
