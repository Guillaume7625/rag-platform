"""Orchestrates hybrid retrieval against Qdrant with tenant/role filters."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.embedding_service import get_embedder
from app.services.qdrant_service import get_qdrant


@dataclass
class RetrievedChunk:
    id: str
    score: float
    payload: dict[str, Any]


class RetrievalService:
    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.qdrant = get_qdrant()

    def retrieve(
        self,
        query: str,
        tenant_id: uuid.UUID,
        allowed_roles: list[str],
        tag_filters: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        emb = self.embedder.embed(query, input_type="query")
        results = self.qdrant.hybrid_search(
            dense=emb["dense"],
            sparse=emb["sparse"],
            tenant_id=tenant_id,
            allowed_roles=allowed_roles,
            limit=top_k or settings.retrieval_top_k,
            tag_filters=tag_filters,
        )
        return [RetrievedChunk(id=r["id"], score=r["score"], payload=r["payload"]) for r in results]


_retrieval: RetrievalService | None = None


def get_retrieval() -> RetrievalService:
    global _retrieval
    if _retrieval is None:
        _retrieval = RetrievalService()
    return _retrieval
