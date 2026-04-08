from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "rag_api",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_routes = {"ingestion.*": {"queue": "ingestion"}}
celery_app.conf.task_default_queue = "api"
