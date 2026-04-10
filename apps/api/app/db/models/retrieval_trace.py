import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetrievalTrace(Base):
    __tablename__ = "retrieval_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE")
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str | None] = mapped_column(String(16))
    retrieved: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    reranked: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Latency breakdown (milliseconds).
    embed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rerank_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generate_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cache hit flags.
    embed_cache_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rerank_cache_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    expansion_queries: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
