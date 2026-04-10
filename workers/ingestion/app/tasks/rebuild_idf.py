from __future__ import annotations

import structlog

from app.services.idf_service import get_idf_service
from app.worker import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.rebuild_idf", bind=True, max_retries=3)
def rebuild_idf_task(self) -> str:
    log.info("rebuild_idf.start")
    try:
        get_idf_service().rebuild_idf_table()
        return "ok"
    except Exception as e:
        log.exception("rebuild_idf.failed", error=str(e))
        raise self.retry(exc=e, countdown=10) from e
