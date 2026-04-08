"""Qdrant client wrapper with hybrid dense + sparse search and ACL filters."""
from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            existing = [c.name for c in self.client.get_collections().collections]
        except Exception as e:  # network/service not ready
            log.warning("qdrant_list_failed", error=str(e))
            return

        if self.collection in existing:
            return

        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": qm.VectorParams(
                    size=settings.embedding_dim,
                    distance=qm.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": qm.SparseVectorParams(
                    index=qm.SparseIndexParams(on_disk=False),
                ),
            },
        )

    def upsert_chunks(self, points: list[dict[str, Any]]) -> None:
        qpoints: list[qm.PointStruct] = []
        for p in points:
            qpoints.append(
                qm.PointStruct(
                    id=p["id"],
                    vector={
                        "dense": p["dense"],
                        "sparse": qm.SparseVector(
                            indices=p["sparse"]["indices"],
                            values=p["sparse"]["values"],
                        ),
                    },
                    payload=p["payload"],
                )
            )
        self.client.upsert(collection_name=self.collection, points=qpoints)

    def delete_by_document(self, document_id: uuid.UUID) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

    def hybrid_search(
        self,
        dense: list[float],
        sparse: dict[str, list],
        tenant_id: uuid.UUID,
        allowed_roles: list[str],
        limit: int,
        tag_filters: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        must: list[qm.Condition] = [
            qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=str(tenant_id)))
        ]
        if allowed_roles:
            must.append(
                qm.FieldCondition(key="allowed_roles", match=qm.MatchAny(any=allowed_roles))
            )
        if tag_filters:
            must.append(qm.FieldCondition(key="tags", match=qm.MatchAny(any=tag_filters)))
        flt = qm.Filter(must=must)

        prefetch = [
            qm.Prefetch(
                query=dense,
                using="dense",
                limit=limit,
                filter=flt,
            ),
            qm.Prefetch(
                query=qm.SparseVector(
                    indices=sparse["indices"], values=sparse["values"]
                ),
                using="sparse",
                limit=limit,
                filter=flt,
            ),
        ]

        res = self.client.query_points(
            collection_name=self.collection,
            prefetch=prefetch,
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
        return [
            {"id": str(p.id), "score": p.score, "payload": p.payload or {}}
            for p in res.points
        ]


_qdrant: QdrantService | None = None


def get_qdrant() -> QdrantService:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantService()
    return _qdrant
