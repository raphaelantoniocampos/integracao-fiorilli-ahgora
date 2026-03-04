from typing import Optional
from uuid import UUID

import dotenv
from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.settings import settings
from app.domain.enums import SyncStatus
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.services.sync_service import SyncService

router = APIRouter()
templates = Jinja2Templates(directory="app/infrastructure/web/templates")


def get_service(db: AsyncSession = Depends(get_service_db := get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)


@router.get("/")
async def dashboard(request: Request, service: SyncService = Depends(get_service)):
    jobs = await service.list_jobs()
    last_run = jobs[0] if jobs else None

    # Total stats instead of daily, since jobs run rarely
    total_jobs = len(jobs)
    success_jobs = len([j for j in jobs if j.status == SyncStatus.SUCCESS])
    failed_jobs = len([j for j in jobs if j.status == SyncStatus.FAILED])

    stats = {
        "last_run_status": last_run.status if last_run else "Nenhuma",
        "total_jobs": total_jobs,
        "success_jobs": success_jobs,
        "failed_jobs": failed_jobs,
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "headless_mode": settings.HEADLESS_MODE,
            "use_cached_files": settings.USE_CACHED_FILES,
            "is_docker": settings.IS_DOCKER,
        },
    )


@router.post("/api/settings/toggle-headless")
async def toggle_headless(request: Request, target: str = Form(...)):
    if settings.IS_DOCKER:
        return {"error": "Ação não permitida em produção"}

    env_path = str(settings.BASE_DIR / ".env")

    if target == "sync":
        settings.HEADLESS_MODE = not settings.HEADLESS_MODE
        dotenv.set_key(env_path, "HEADLESS_MODE", str(settings.HEADLESS_MODE))
    elif target == "tasks":
        settings.HEADLESS_MODE_TASKS = not settings.HEADLESS_MODE_TASKS
        dotenv.set_key(
            env_path, "HEADLESS_MODE_TASKS", str(settings.HEADLESS_MODE_TASKS)
        )

    response = templates.TemplateResponse(
        f"partials/headless_{target}_toggle.html",
        {
            "request": request,
            "headless_mode": settings.HEADLESS_MODE,
            "headless_mode_tasks": settings.HEADLESS_MODE_TASKS,
            "use_cached_files": settings.USE_CACHED_FILES,
            "is_docker": settings.IS_DOCKER,
        },
    )
    response.headers["HX-Trigger"] = "refresh"
    return response


@router.post("/api/settings/toggle-cached")
async def toggle_cached_files(request: Request):
    if settings.IS_DOCKER:
        return {"error": "Ação não permitida em produção"}

    env_path = str(settings.BASE_DIR / ".env")
    settings.USE_CACHED_FILES = not settings.USE_CACHED_FILES
    dotenv.set_key(env_path, "USE_CACHED_FILES", str(settings.USE_CACHED_FILES))

    response = templates.TemplateResponse(
        "partials/use_cached_files_toggle.html",
        {
            "request": request,
            "use_cached_files": settings.USE_CACHED_FILES,
            "is_docker": settings.IS_DOCKER,
        },
    )
    response.headers["HX-Trigger"] = "refresh"
    return response


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
    from typing import Any, Dict

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
            "headless_mode_tasks": settings.HEADLESS_MODE_TASKS,
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


@router.get("/partials/task-payload")
async def get_task_details_partial(
    request: Request,
    task_id: Optional[UUID] = None,
    service: SyncService = Depends(get_service),
):
    if task_id:
        task = await service.repo.get_task(task_id)
        if task:
            return templates.TemplateResponse(
                "task_payload.html",
                {
                    "request": request,
                    "task": task,
                    "task_id": str(task_id) if task_id else None,
                },
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
    request: Request, job_id: UUID, task_type: Optional[str] = None, service: SyncService = Depends(get_service)
):
    logs = await service.get_job_logs(job_id)
    if task_type:
        tasks = await service.get_automation_tasks(job_id)
        valid_task_ids = {
            str(t.id) for t in tasks 
            if str(t.type).upper() == task_type.upper() or getattr(t.type, "name", str(t.type)).upper() == task_type.upper()
        }
        logs = [
            log for log in logs 
            if (log.task_id and str(log.task_id) in valid_task_ids) or not log.task_id
        ]
        
    job_status = await service.get_job_status(job_id)
    return templates.TemplateResponse(
        "logs_partial.html",
        {
            "request": request,
            "logs": logs,
            "job_id": str(job_id),
            "job_status": job_status,
            "task_type": task_type,
        },
    )


@router.get("/partials/log-entries")
async def get_log_entries_partial(
    request: Request,
    job_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    task_type: Optional[str] = None,
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
        if task_type:
            tasks = await service.get_automation_tasks(job_id)
            valid_task_ids = {
                str(t.id) for t in tasks 
                if str(t.type).upper() == task_type.upper() or getattr(t.type, "name", str(t.type)).upper() == task_type.upper()
            }
            logs = [
                log for log in logs 
                if (log.task_id and str(log.task_id) in valid_task_ids) or not log.task_id
            ]
        return templates.TemplateResponse(
            "log_entries_partial.html",
            {"request": request, "logs": logs, "job_id": str(job_id), "task_type": task_type},
        )

    return templates.TemplateResponse(
        "log_entries_partial.html", {"request": request, "logs": []}
    )
