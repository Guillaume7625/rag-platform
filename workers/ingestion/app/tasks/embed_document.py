from __future__ import annotations

import structlog
from sqlalchemy import text

from app.db import session_scope
from app.services.embedder import get_embedder
from app.worker import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.embed_document", bind=True, max_retries=3)
def embed_document_task(self, document_id: str, version_id: str, chunks: list[dict]) -> str:
    log.info("embed_document.start", document_id=document_id, n=len(chunks))
    try:
        embedder = get_embedder()
        contents = [c["content"] for c in chunks]
        denses = embedder.embed_dense_batch(contents, input_type="document")
        enriched: list[dict] = [
            {**c, "dense": dense, "sparse": embedder.embed_sparse(c["content"])}
            for c, dense in zip(chunks, denses, strict=True)
        ]

        # Do NOT set state='indexed' here. Only index_document may do that.
        celery_app.send_task(
            "ingestion.index_document",
            args=[document_id, version_id, enriched],
        )
        return "ok"
    except Exception as e:
        log.exception("embed_document.failed", error=str(e))
        with session_scope() as db:
            db.execute(
                text("UPDATE documents SET state = 'failed', error = :err WHERE id = :id"),
                {"err": str(e)[:1000], "id": document_id},
            )
        raise self.retry(exc=e, countdown=10) from e
