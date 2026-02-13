from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import SyncJob
from app.services.sync_service import SyncService
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.database import get_db

router = APIRouter()

def get_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)

@router.post("/run", response_model=SyncJob)
async def run_sync_job(
    background_tasks: BackgroundTasks,
    service: SyncService = Depends(get_service)
):
    job = await service.create_job(triggered_by="api")
    background_tasks.add_task(service.run_sync_background, job.id)
    return job

@router.get("/jobs", response_model=list[SyncJob])
async def list_jobs(service: SyncService = Depends(get_service)):
    return await service.list_jobs()

@router.get("/jobs/{job_id}", response_model=SyncJob)
async def get_job(job_id: UUID, service: SyncService = Depends(get_service)):
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
