from datetime import datetime
from uuid import UUID
from typing import Optional
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


@router.get("/jobs/{job_id}/tasks")
async def get_task_groups_page(
    request: Request, job_id: UUID, service: SyncService = Depends(get_service)
):
    from collections import defaultdict
    from typing import Dict, Any
    from app.domain.enums import AutomationTaskStatus

    tasks = await service.get_automation_tasks(job_id)

    groups: Dict[Any, Dict[str, Any]] = defaultdict(
        lambda: {
            "type": "",
            "total": 0,
            "pending": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "cancelled": 0,
        }
    )

    for t in tasks:
        group = groups[t.type]
        group["type"] = t.type
        group["total"] += 1

        if t.status == AutomationTaskStatus.PENDING:
            group["pending"] += 1
        elif t.status == AutomationTaskStatus.RUNNING:
            group["running"] += 1
        elif t.status == AutomationTaskStatus.SUCCESS:
            group["success"] += 1
        elif t.status == AutomationTaskStatus.FAILED:
            group["failed"] += 1
        elif t.status == AutomationTaskStatus.CANCELLED:
            group["cancelled"] += 1

    return templates.TemplateResponse(
        "task_groups_page.html",
        {
            "request": request,
            "task_groups": list(groups.values()),
            "job_id": str(job_id),
        },
    )


@router.get("/partials/task-details-inline")
async def get_task_details_inline_partial(
    request: Request,
    job_id: UUID,
    task_type: str,
    service: SyncService = Depends(get_service),
):
    tasks = await service.get_automation_tasks(job_id)
    # Filter by Enum name or value to be safe
    filtered_tasks = [
        t
        for t in tasks
        if str(t.type) == task_type
        or getattr(t.type, "value", str(t.type)) == task_type
        or getattr(t.type, "name", str(t.type)) == task_type
    ]

    return templates.TemplateResponse(
        "task_details_inline_partial.html",
        {
            "request": request,
            "tasks": filtered_tasks,
            "task_type": task_type,
            "job_id": str(job_id),
        },
    )

@router.get("/partials/task-details")
async def get_task_details_partial(
    request: Request, task_id: UUID, service: SyncService = Depends(get_service)
):
    task = await service.repo.get_task(task_id)
    return templates.TemplateResponse(
        "task_details.html",
        {"request": request, "task": [task], "task_id": str(task_id)},
    )


@router.get("/partials/task-log")
async def get_task_log_partial(
    request: Request, task_id: UUID, service: SyncService = Depends(get_service)
):
    task = await service.repo.get_task(task_id)
    logs = await service.repo.get_task_logs(task_id)
    return templates.TemplateResponse(
        "task_log_partial.html",
        {"request": request, "task": task, "logs": logs, "task_id": str(task_id)},
    )


@router.get("/partials/logs")
async def get_logs_partial(
    request: Request, job_id: UUID, service: SyncService = Depends(get_service)
):
    logs = await service.get_job_logs(job_id)
    job_status = await service.get_job_status(job_id)
    return templates.TemplateResponse(
        "logs_partial.html",
        {
            "request": request,
            "logs": logs,
            "job_id": str(job_id),
            "job_status": job_status,
        },
    )


@router.get("/partials/log-entries")
async def get_log_entries_partial(
    request: Request,
    job_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    service: SyncService = Depends(get_service),
):
    if task_id:
        logs = await service.repo.get_task_logs(task_id)
        return templates.TemplateResponse(
            "log_entries_partial.html",
            {"request": request, "logs": logs, "task_id": str(task_id)},
        )
    if job_id:
        logs = await service.get_job_logs(job_id)
        return templates.TemplateResponse(
            "log_entries_partial.html",
            {"request": request, "logs": logs, "job_id": str(job_id)},
        )

    return templates.TemplateResponse(
        "log_entries_partial.html", {"request": request, "logs": []}
    )
