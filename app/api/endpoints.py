from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import SyncJob, SyncLog
from app.services.sync_service import SyncService
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.database import get_db

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)


@router.post("/run", response_model=SyncJob)
async def run_sync_job(
    background_tasks: BackgroundTasks, service: SyncService = Depends(get_service)
):
    job = await service.create_job(triggered_by="api")
    background_tasks.add_task(SyncService.run_sync_task_standalone, job.id)
    return job


@router.get("/jobs", response_model=list[SyncJob])
async def list_jobs(service: SyncService = Depends(get_service)):
    return await service.list_jobs()


@router.post("/jobs/{job_id}/kill")
async def kill_job(job_id: UUID, service: SyncService = Depends(get_service)):
    success = await service.kill_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not running")
    return {"message": f"Kill signal sent to job {job_id}"}


@router.post("/kill-all")
async def kill_all_jobs(service: SyncService = Depends(get_service)):
    count = await service.kill_all_jobs()
    return {"message": f"Kill signal sent to {count} active jobs"}


@router.get("/jobs/{job_id}/logs", response_model=list[SyncLog])
async def get_job_logs(job_id: UUID, service: SyncService = Depends(get_service)):
    return await service.get_job_logs(job_id)
