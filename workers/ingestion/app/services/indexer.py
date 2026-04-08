from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings


def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection in existing:
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            "dense": qm.VectorParams(size=settings.embedding_dim, distance=qm.Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": qm.SparseVectorParams(index=qm.SparseIndexParams(on_disk=False)),
        },
    )


def upsert_points(client: QdrantClient, points: list[dict]) -> None:
    q_points: list[qm.PointStruct] = []
    for p in points:
        q_points.append(
            qm.PointStruct(
                id=p["id"],
                vector={
                    "dense": p["dense"],
                    "sparse": qm.SparseVector(
                        indices=p["sparse"]["indices"], values=p["sparse"]["values"]
                    ),
                },
                payload=p["payload"],
            )
        )
    client.upsert(collection_name=settings.qdrant_collection, points=q_points)


def delete_by_document(client: QdrantClient, document_id: str) -> None:
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qm.FilterSelector(
            filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="document_id",
                        match=qm.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )
