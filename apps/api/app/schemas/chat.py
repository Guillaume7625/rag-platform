from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: UUID
    document_name: str
    page: int | None = None
    chunk_id: UUID
    excerpt: str


class ChatQueryRequest(BaseModel):
    query: str
    conversation_id: UUID | None = None
    filters: dict = Field(default_factory=dict)
    force_mode: str | None = None  # "standard" | "deep"


class ChatQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    mode_used: str
    latency_ms: int
    conversation_id: UUID
    message_id: UUID
