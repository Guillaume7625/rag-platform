"""High-level document lifecycle operations used by routes."""
from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.services.storage_service import get_storage
from app.tasks.celery_app import celery_app


class DocumentService:
    def create_from_upload(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        content: bytes,
        mime_type: str,
        tags: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Document:
        sha = hashlib.sha256(content).hexdigest()
        storage = get_storage()
        key = storage.put_object(tenant_id, filename, content, mime_type)

        doc = Document(
            tenant_id=tenant_id,
            name=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=sha,
            storage_key=key,
            state="uploaded",
            tags=tags or [],
            allowed_roles=allowed_roles or ["member"],
            uploaded_by=user_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Fire ingestion pipeline (parse -> chunk -> embed -> index).
        celery_app.send_task("ingestion.parse_document", args=[str(doc.id)])
        return doc

    def reindex(self, db: Session, document: Document) -> None:
        document.state = "parsing"
        document.error = None
        db.add(document)
        db.commit()
        celery_app.send_task("ingestion.parse_document", args=[str(document.id)])

    def delete(self, db: Session, document: Document) -> None:
        storage = get_storage()
        try:
            storage.delete_object(document.storage_key)
        except Exception:
            pass
        celery_app.send_task("ingestion.delete_document_index", args=[str(document.id)])
        db.delete(document)
        db.commit()


_doc_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    global _doc_service
    if _doc_service is None:
        _doc_service = DocumentService()
    return _doc_service
