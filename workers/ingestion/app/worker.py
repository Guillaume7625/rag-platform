import structlog
from celery import Celery

from app.config import settings

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

celery_app = Celery(
    "rag_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.parse_document",
        "app.tasks.chunk_document",
        "app.tasks.embed_document",
        "app.tasks.index_document",
        "app.tasks.delete_document",
        "app.tasks.rebuild_idf",
    ],
)

celery_app.conf.task_routes = {"ingestion.*": {"queue": "ingestion"}}
celery_app.conf.worker_concurrency = settings.celery_concurrency
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
