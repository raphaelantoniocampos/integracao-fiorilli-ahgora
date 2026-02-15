from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import traceback
import logging

from app.api.endpoints import router as api_router
from app.infrastructure.web.routes import router as web_router
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(web_router)
app.include_router(api_router, prefix="/api/sync", tags=["sync"])


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
