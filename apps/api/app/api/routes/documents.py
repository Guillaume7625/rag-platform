import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.models.chunk import DocumentChunkParent
from app.db.models.document import Document
from app.db.session import get_db
from app.schemas.document import (
    DocumentChunkOut,
    DocumentChunksResponse,
    DocumentListResponse,
    DocumentOut,
)
from app.services.document_service import get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])

# Hard cap on chunk `content` returned by the list-chunks endpoint. Full chunk
# content stays in Postgres and is never exposed via this route.
CHUNK_CONTENT_PREVIEW_CHARS = 500


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Form(""),
    allowed_roles: str = Form("member"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    svc = get_document_service()
    doc = svc.create_from_upload(
        db=db,
        tenant_id=current.tenant_id,
        user_id=current.id,
        filename=file.filename or "upload.bin",
        content=content,
        mime_type=file.content_type or "application/octet-stream",
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        allowed_roles=[r.strip() for r in allowed_roles.split(",") if r.strip()],
    )
    return DocumentOut.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    state: str | None = Query(default=None, description="Filter by lifecycle state."),
    tags: list[str] | None = Query(
        default=None,
        description="Repeated query param. Document must contain ALL given tags.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    # Tenant isolation is enforced on every query below. Any additional filter
    # is applied on top, so total/items remain consistent with the envelope.
    q = db.query(Document).filter(Document.tenant_id == current.tenant_id)
    if state is not None:
        q = q.filter(Document.state == state)
    if tags:
        # JSONB containment: document.tags must be a superset of the requested
        # tag list (AND semantics, not OR).
        q = q.filter(Document.tags.contains(tags))

    total = q.count()
    rows = q.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    items = [DocumentOut.model_validate(d) for d in rows]
    return DocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = _must_get(db, doc_id, current.tenant_id)
    return DocumentOut.model_validate(doc)


@router.get("/{doc_id}/chunks", response_model=DocumentChunksResponse)
def list_document_chunks(
    doc_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChunksResponse:
    # Tenant ownership is enforced by _must_get BEFORE any chunk row is read.
    # Returns parent chunks only (the LLM-facing unit), ordered by order_index.
    _must_get(db, doc_id, current.tenant_id)

    q = db.query(DocumentChunkParent).filter(DocumentChunkParent.document_id == doc_id)
    total = q.count()
    rows = (
        q.order_by(DocumentChunkParent.order_index.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: list[DocumentChunkOut] = []
    for row in rows:
        full = row.content or ""
        preview = full[:CHUNK_CONTENT_PREVIEW_CHARS]
        items.append(
            DocumentChunkOut(
                id=row.id,
                order_index=row.order_index,
                page=row.page,
                section_title=row.section_title,
                content=preview,
                token_count=row.token_count,
                truncated=len(full) > CHUNK_CONTENT_PREVIEW_CHARS,
            )
        )

    return DocumentChunksResponse(
        document_id=doc_id,
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.post("/{doc_id}/reindex", response_model=DocumentOut)
def reindex_document(
    doc_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = _must_get(db, doc_id, current.tenant_id)
    get_document_service().reindex(db, doc)
    return DocumentOut.model_validate(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    doc = _must_get(db, doc_id, current.tenant_id)
    get_document_service().delete(db, doc)


def _must_get(db: Session, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.tenant_id == tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
    return doc
