import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.settings import settings
from app.core.task_registry import task_registry
from app.domain.entities import AutomationTask, SyncJob, SyncLog
from app.domain.enums import AutomationTaskStatus
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.services.transport_crypto import transport_crypto
from app.services.credential_crypto import (
    store_credentials_in_metadata,
    decrypt_password,
)
from app.services.sync_service import SyncService
from app.services.task_execution_service import TaskExecutionService


class SyncCredentials(BaseModel):
    fiorilli_user: str
    fiorilli_password: str
    fiorilli_url: Optional[str] = None
    ahgora_user: str
    ahgora_password: str
    ahgora_company: str
    ahgora_url: Optional[str] = None


router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)


@router.get(
    "/public-key",
    summary="Get Public Key",
    description="Returns the RSA public key in PEM format for frontend encryption.",
)
async def get_public_key():
    return {"public_key": transport_crypto.get_public_key_pem()}


@router.post(
    "/run",
    response_model=SyncJob,
    summary="Trigger Sync Job",
    description="Starts a background job to download data from Fiorilli and Ahgora and perform analysis.",
)
async def run_sync_job(
    request: Request,
    background_tasks: BackgroundTasks,
    service: SyncService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    # Get the current user
    username = request.state.username
    repo = SqlAlchemyRepo(db)
    user = await repo.get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Get the user's credentials from the database
    credentials_dict = await repo.get_user_credentials(user.id)
    if credentials_dict is None:
        raise HTTPException(status_code=400, detail="User credentials not found")

    # Decrypt passwords
    fiorilli_password = None
    ahgora_password = None
    if credentials_dict.get("fiorilli_password_encrypted"):
        try:
            fiorilli_password = decrypt_password(
                credentials_dict["fiorilli_password_encrypted"]
            )
        except Exception as e:
            logger.error(f"Failed to decrypt Fiorilli password for user {user.id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to decrypt Fiorilli password"
            )
    if credentials_dict.get("ahgora_password_encrypted"):
        try:
            ahgora_password = decrypt_password(
                credentials_dict["ahgora_password_encrypted"]
            )
        except Exception as e:
            logger.error(f"Failed to decrypt Ahgora password for user {user.id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to decrypt Ahgora password"
            )

    # Get URLs and usernames, fallback to settings if not set
    fiorilli_url = credentials_dict.get("fiorilli_url") or settings.FIORILLI_URL
    fiorilli_user = credentials_dict.get("fiorilli_user") or settings.FIORILLI_USER
    ahgora_url = credentials_dict.get("ahgora_url") or settings.AHGORA_URL
    ahgora_user = credentials_dict.get("ahgora_user") or settings.AHGORA_USER
    ahgora_company = credentials_dict.get("ahgora_company") or settings.AHGORA_COMPANY

    # Create job and associate with user
    job = await service.create_job(triggered_by="api")
    job.user_id = user.id
    await service.repo.save_job(job)

    # Store credentials in job metadata for retry purposes (encrypted)
    store_credentials_in_metadata(job.metadata, fiorilli_password, ahgora_password)

    # Run the sync task in the background
    background_tasks.add_task(
        SyncService.run_sync_task_standalone,
        job.id,
        fiorilli_url,
        fiorilli_user,
        fiorilli_password,
        ahgora_url,
        ahgora_user,
        ahgora_company,
        ahgora_password,
    )
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
    "/jobs/kill-all",
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


def get_execution_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return TaskExecutionService(repo=repo)


async def _run_batch_standalone(
    job_id: UUID,
    task_type: str,
    fiorilli_url: Optional[str] = None,
    fiorilli_user: Optional[str] = None,
    fiorilli_password: Optional[str] = None,
    ahgora_url: Optional[str] = None,
    ahgora_user: Optional[str] = None,
    ahgora_company: Optional[str] = None,
    ahgora_password: Optional[str] = None,
):
    from app.core.database import async_session_factory
    from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo

    async with async_session_factory() as session:
        repo = SqlAlchemyRepo(session)
        service = TaskExecutionService(repo=repo)
        await service.execute_batch(
            job_id,
            task_type,
            fiorilli_url=fiorilli_url,
            fiorilli_user=fiorilli_user,
            fiorilli_password=fiorilli_password,
            ahgora_url=ahgora_url,
            ahgora_user=ahgora_user,
            ahgora_company=ahgora_company,
            ahgora_password=ahgora_password,
        )


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
    credentials: SyncCredentials = Body(...),
):
    try:
        decrypted_fiorilli = transport_crypto.decrypt(credentials.fiorilli_password)
        decrypted_ahgora = transport_crypto.decrypt(credentials.ahgora_password)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid credential encryption payload"
        )

    fiorilli_url = credentials.fiorilli_url or settings.FIORILLI_URL
    ahgora_url = credentials.ahgora_url or settings.AHGORA_URL

    # Execute batch in background with a new db session
    background_tasks.add_task(
        _run_batch_standalone,
        job_id,
        task_type,
        fiorilli_url,
        credentials.fiorilli_user,
        decrypted_fiorilli,
        ahgora_url,
        credentials.ahgora_user,
        credentials.ahgora_company,
        decrypted_ahgora,
    )
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
    "/tasks/job/{job_id}/cancel-all",
    summary="Cancel All Automation Tasks for a Job",
    description="Cancels all pending, running or failed automation tasks associated with a specific job.",
    tags=["Automation Tasks"],
)
async def cancel_all_job_tasks(
    job_id: UUID,
    service: TaskExecutionService = Depends(get_execution_service),
):
    await service.cancel_all_for_job(job_id)
    return {"message": f"All tasks cancelled for job {job_id}"}


async def _run_task_standalone(
    task_id: UUID,
    fiorilli_url: Optional[str] = None,
    fiorilli_user: Optional[str] = None,
    fiorilli_password: Optional[str] = None,
    ahgora_url: Optional[str] = None,
    ahgora_user: Optional[str] = None,
    ahgora_company: Optional[str] = None,
    ahgora_password: Optional[str] = None,
):
    from app.core.database import async_session_factory
    from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo

    async with async_session_factory() as session:
        repo = SqlAlchemyRepo(session)
        service = TaskExecutionService(repo=repo)
        await service.execute_task(
            task_id,
            fiorilli_url=fiorilli_url,
            fiorilli_user=fiorilli_user,
            fiorilli_password=fiorilli_password,
            ahgora_url=ahgora_url,
            ahgora_user=ahgora_user,
            ahgora_company=ahgora_company,
            ahgora_password=ahgora_password,
        )


@router.post(
    "/tasks/{task_id}/execute",
    summary="Execute Automation Task",
    description="Manually triggers the execution of a specific automation task via Selenium in the background.",
    tags=["Automation Tasks"],
)
async def execute_task(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    credentials: SyncCredentials = Body(...),
):
    try:
        decrypted_fiorilli = transport_crypto.decrypt(credentials.fiorilli_password)
        decrypted_ahgora = transport_crypto.decrypt(credentials.ahgora_password)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid credential encryption payload"
        )

    fiorilli_url = credentials.fiorilli_url or settings.FIORILLI_URL
    ahgora_url = credentials.ahgora_url or settings.AHGORA_URL

    # Execute in background with a new db session
    background_tasks.add_task(
        _run_task_standalone,
        task_id,
        fiorilli_url,
        credentials.fiorilli_user,
        decrypted_fiorilli,
        ahgora_url,
        credentials.ahgora_user,
        credentials.ahgora_company,
        decrypted_ahgora,
    )
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
