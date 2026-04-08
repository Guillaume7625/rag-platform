from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = None
    mode_used: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)
