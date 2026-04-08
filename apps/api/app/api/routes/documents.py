import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.models.document import Document
from app.db.session import get_db
from app.schemas.document import DocumentListResponse, DocumentOut
from app.services.document_service import get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])


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
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    q = db.query(Document).filter(Document.tenant_id == current.tenant_id)
    items = q.order_by(Document.created_at.desc()).all()
    return DocumentListResponse(
        items=[DocumentOut.model_validate(d) for d in items],
        total=len(items),
    )


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = _must_get(db, doc_id, current.tenant_id)
    return DocumentOut.model_validate(doc)


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
