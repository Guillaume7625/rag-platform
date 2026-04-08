from __future__ import annotations

import uuid

import structlog
from sqlalchemy import text

from app.db import session_scope
from app.services.parser import parse_document
from app.services.storage import get_object_bytes
from app.worker import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.parse_document", bind=True, max_retries=3)
def parse_document_task(self, document_id: str) -> str:
    log.info("parse_document.start", document_id=document_id)
    try:
        with session_scope() as db:
            row = db.execute(
                text("SELECT storage_key, mime_type, name FROM documents WHERE id = :id"),
                {"id": document_id},
            ).first()
            if not row:
                log.warning("parse_document.not_found", document_id=document_id)
                return "missing"

            # Set state to 'parsing' before doing work.
            db.execute(
                text("UPDATE documents SET state = 'parsing' WHERE id = :id"),
                {"id": document_id},
            )

            storage_key, mime_type, name = row
            content = get_object_bytes(storage_key)
            sections = parse_document(content, mime_type or "application/octet-stream", name)

            # Stash the parsed sections in a document_versions row, then move on.
            version_id = str(uuid.uuid4())
            db.execute(
                text(
                    "INSERT INTO document_versions (id, document_id, version) "
                    "VALUES (:id, :doc, 1)"
                ),
                {"id": version_id, "doc": document_id},
            )
            db.execute(
                text("UPDATE documents SET state = 'chunking' WHERE id = :id"),
                {"id": document_id},
            )

            # Hand off. We pass the parsed sections directly to avoid re-parsing.
            celery_app.send_task(
                "ingestion.chunk_document",
                args=[
                    document_id,
                    version_id,
                    [
                        {
                            "order": s.order,
                            "page": s.page,
                            "section_title": s.section_title,
                            "text": s.text,
                        }
                        for s in sections
                    ],
                ],
            )
            return "ok"
    except Exception as e:
        log.exception("parse_document.failed", error=str(e))
        with session_scope() as db:
            db.execute(
                text("UPDATE documents SET state = 'failed', error = :err WHERE id = :id"),
                {"err": str(e)[:1000], "id": document_id},
            )
        raise self.retry(exc=e, countdown=10) from e
