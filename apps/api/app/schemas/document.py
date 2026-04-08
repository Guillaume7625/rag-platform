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
    items: list[DocumentOut]
    total: int
