from __future__ import annotations

import structlog

from app.services.indexer import delete_by_document, get_client
from app.worker import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.delete_document_index", bind=True, max_retries=2)
def delete_document_index_task(self, document_id: str) -> str:
    log.info("delete_document_index.start", document_id=document_id)
    try:
        client = get_client()
        delete_by_document(client, document_id)
        return "ok"
    except Exception as e:
        log.exception("delete_document_index.failed", error=str(e))
        raise self.retry(exc=e, countdown=10) from e
