from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.sync_service import SyncService
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.database import get_db
from app.domain.enums import SyncStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/infrastructure/web/templates")


def get_service(db: AsyncSession = Depends(get_service_db := get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)


@router.get("/")
async def dashboard(request: Request, service: SyncService = Depends(get_service)):
    jobs = await service.list_jobs()
    last_run = jobs[0] if jobs else None

    # Simple stats for the cards
    today = datetime.now().date()
    jobs_today = [j for j in jobs if j.created_at.date() == today]
    success_today = len([j for j in jobs_today if j.status == SyncStatus.SUCCESS])

    stats = {
        "last_run_status": last_run.status if last_run else "Nenhuma",
        "success_today": success_today,
    }

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stats": stats}
    )


@router.get("/partials/jobs")
async def get_jobs_partial(
    request: Request, service: SyncService = Depends(get_service)
):
    jobs = await service.list_jobs()
    return templates.TemplateResponse(
        "jobs_partial.html", {"request": request, "jobs": jobs}
    )


@router.get("/partials/tasks")
async def get_tasks_partial(
    request: Request, job_id: UUID, service: SyncService = Depends(get_service)
):
    tasks = await service.get_automation_tasks(job_id)
    return templates.TemplateResponse(
        "tasks_partial.html",
        {"request": request, "tasks": tasks, "job_id": str(job_id)},
    )


@router.get("/partials/logs")
async def get_logs_partial(
    request: Request, job_id: UUID, service: SyncService = Depends(get_service)
):
    logs = await service.get_job_logs(job_id)
    job_status = await service.get_job_status(job_id)
    return templates.TemplateResponse(
        "logs_partial.html", {"request": request, "logs": logs, "job_id": str(job_id), "job_status": job_status}
    )


@router.get("/partials/log-entries")
async def get_log_entries_partial(
    request: Request, job_id: UUID, service: SyncService = Depends(get_service)
):
    logs = await service.get_job_logs(job_id)
    return templates.TemplateResponse(
        "log_entries_partial.html",
        {"request": request, "logs": logs, "job_id": str(job_id)},
    )
