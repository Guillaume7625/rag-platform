from __future__ import annotations

import structlog
from sqlalchemy import text

from app.db import session_scope
from app.services.indexer import ensure_collection, get_client, upsert_points
from app.worker import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.index_document", bind=True, max_retries=3)
def index_document_task(self, document_id: str, version_id: str, chunks: list[dict]) -> str:
    log.info("index_document.start", document_id=document_id, n=len(chunks))
    try:
        client = get_client()
        ensure_collection(client)

        # Load ACL metadata from Postgres.
        with session_scope() as db:
            row = db.execute(
                text(
                    "SELECT tenant_id, name, tags, allowed_roles FROM documents WHERE id = :id"
                ),
                {"id": document_id},
            ).first()
            if not row:
                log.warning("index_document.missing_doc", document_id=document_id)
                return "missing"
            tenant_id, name, tags, allowed_roles = row

        points = []
        for c in chunks:
            points.append(
                {
                    "id": c["chunk_id"],
                    "dense": c["dense"],
                    "sparse": c["sparse"],
                    "payload": {
                        "chunk_id": c["chunk_id"],
                        "parent_id": c["parent_id"],
                        "document_id": document_id,
                        "document_version_id": version_id,
                        "tenant_id": str(tenant_id),
                        "page": c.get("page"),
                        "section_title": c.get("section_title"),
                        "tags": tags or [],
                        "source_name": name,
                        "allowed_roles": allowed_roles or ["member"],
                        "content": c["content"],
                    },
                }
            )

        if points:
            upsert_points(client, points)

        with session_scope() as db:
            db.execute(
                text("UPDATE documents SET state = 'indexed' WHERE id = :id"),
                {"id": document_id},
            )
        return "ok"
    except Exception as e:
        log.exception("index_document.failed", error=str(e))
        with session_scope() as db:
            db.execute(
                text("UPDATE documents SET state = 'failed', error = :err WHERE id = :id"),
                {"err": str(e)[:1000], "id": document_id},
            )
        raise self.retry(exc=e, countdown=10) from e
