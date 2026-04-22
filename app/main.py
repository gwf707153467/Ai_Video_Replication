import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.storage_service import StorageService
from app.web_ui import render_studio_page

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def bootstrap_storage() -> None:
    try:
        response = StorageService().ensure_buckets()
        logger.info("storage bootstrap completed", extra={"buckets": [item.bucket_name for item in response.buckets]})
    except Exception as exc:
        logger.warning("storage bootstrap skipped: %s", exc)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "target_market": settings.default_target_market,
        "target_language": settings.default_target_language,
    }


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/studio", response_class=HTMLResponse, include_in_schema=False)
def studio_page() -> HTMLResponse:
    return HTMLResponse(render_studio_page())


app.include_router(api_router, prefix="/api/v1")
