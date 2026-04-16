from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai_videos_replication",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.imports = ("app.workers.tasks",)

# Ensure decorator-based task registration is loaded when the worker starts.
import app.workers.tasks  # noqa: E402,F401
