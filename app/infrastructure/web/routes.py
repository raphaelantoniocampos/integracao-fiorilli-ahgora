from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.sync_service import SyncService
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/infrastructure/web/templates")


def get_service(db: AsyncSession = Depends(get_db)):
    repo = SqlAlchemyRepo(db)
    return SyncService(repo=repo)


@router.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/partials/jobs")
async def get_jobs_partial(
    request: Request, service: SyncService = Depends(get_service)
):
    jobs = await service.list_jobs()
    return templates.TemplateResponse(
        "jobs_partial.html", {"request": request, "jobs": jobs}
    )
