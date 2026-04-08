from __future__ import annotations

import uuid

import structlog
from sqlalchemy import text

from app.db import session_scope
from app.services.chunker import chunk_sections
from app.services.parser import ParsedSection
from app.worker import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.chunk_document", bind=True, max_retries=3)
def chunk_document_task(self, document_id: str, version_id: str, sections: list[dict]) -> str:
    log.info("chunk_document.start", document_id=document_id)
    try:
        parsed = [
            ParsedSection(
                order=s["order"],
                page=s.get("page"),
                section_title=s.get("section_title"),
                text=s["text"],
            )
            for s in sections
        ]
        parents = chunk_sections(parsed)

        child_payloads: list[dict] = []
        with session_scope() as db:
            for parent in parents:
                parent_id = str(uuid.uuid4())
                db.execute(
                    text(
                        "INSERT INTO document_chunks_parent "
                        "(id, document_id, document_version_id, order_index, page, section_title, content, token_count) "
                        "VALUES (:id, :doc, :ver, :ord, :pg, :sec, :content, :toks)"
                    ),
                    {
                        "id": parent_id,
                        "doc": document_id,
                        "ver": version_id,
                        "ord": parent.order,
                        "pg": parent.page,
                        "sec": parent.section_title,
                        "content": parent.content,
                        "toks": parent.token_count,
                    },
                )
                for child in parent.children:
                    child_id = str(uuid.uuid4())
                    db.execute(
                        text(
                            "INSERT INTO document_chunks_child "
                            "(id, parent_id, document_id, order_index, content, token_count) "
                            "VALUES (:id, :pid, :doc, :ord, :content, :toks)"
                        ),
                        {
                            "id": child_id,
                            "pid": parent_id,
                            "doc": document_id,
                            "ord": child.order,
                            "content": child.content,
                            "toks": child.token_count,
                        },
                    )
                    child_payloads.append(
                        {
                            "chunk_id": child_id,
                            "parent_id": parent_id,
                            "page": parent.page,
                            "section_title": parent.section_title,
                            "content": child.content,
                        }
                    )

            db.execute(
                text("UPDATE documents SET state = 'embedding' WHERE id = :id"),
                {"id": document_id},
            )

        celery_app.send_task(
            "ingestion.embed_document",
            args=[document_id, version_id, child_payloads],
        )
        return "ok"
    except Exception as e:
        log.exception("chunk_document.failed", error=str(e))
        with session_scope() as db:
            db.execute(
                text("UPDATE documents SET state = 'failed', error = :err WHERE id = :id"),
                {"err": str(e)[:1000], "id": document_id},
            )
        raise self.retry(exc=e, countdown=10) from e
