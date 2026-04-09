from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: UUID
    name: str
    mime_type: str | None = None
    size_bytes: int | None = None
    state: str
    tags: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Paginated envelope for GET /documents.

    has_more is derived server-side so clients never re-compute it.
    """

    items: list[DocumentOut]
    total: int
    limit: int
    offset: int
    has_more: bool


class DocumentChunkOut(BaseModel):
    """A single parent chunk as returned to the document-viewer UI.

    `content` is truncated server-side (see CHUNK_CONTENT_PREVIEW_CHARS in
    the documents route). `truncated` is True when the original chunk text
    exceeded that limit, so the UI can render a "view full chunk" affordance
    without a second request.
    """

    id: UUID
    order_index: int
    page: int | None = None
    section_title: str | None = None
    content: str
    token_count: int | None = None
    truncated: bool


class DocumentChunksResponse(BaseModel):
    """Paginated envelope for GET /documents/{id}/chunks.

    Envelope fields (items/total/limit/offset/has_more) are intentionally
    identical to DocumentListResponse so a frontend can share one
    paginated-list component across both endpoints.
    """

    document_id: UUID
    items: list[DocumentChunkOut]
    total: int
    limit: int
    offset: int
    has_more: bool
