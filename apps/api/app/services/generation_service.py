"""Generation step: packs context, calls the LLM, produces citations."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.chunk import DocumentChunkParent
from app.schemas.chat import Citation
from app.services.llm_provider import get_llm

SYSTEM_PROMPT = (
    "You are a careful assistant. Answer the user's question using ONLY the "
    "provided context. Cite sources by their [n] identifier. If the context "
    "does not contain the answer, say you don't know."
)


@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation]
    confidence: float


class GenerationService:
    def __init__(self) -> None:
        self.llm = get_llm()

    def pack_and_generate(
        self,
        db: Session,
        query: str,
        reranked: list[dict[str, Any]],
        large: bool = False,
    ) -> GenerationResult:
        # Collapse child chunks to unique parent contexts, preserving order.
        selected: list[dict[str, Any]] = []
        seen_parents: set[str] = set()
        for r in reranked:
            pid = r["payload"].get("parent_id")
            if pid in seen_parents:
                continue
            seen_parents.add(pid)
            selected.append(r)

        # Load parent content + document metadata from Postgres.
        parent_ids = [uuid.UUID(r["payload"]["parent_id"]) for r in selected if r["payload"].get("parent_id")]
        parents: dict[uuid.UUID, DocumentChunkParent] = {}
        if parent_ids:
            for p in db.query(DocumentChunkParent).filter(DocumentChunkParent.id.in_(parent_ids)).all():
                parents[p.id] = p

        context_blocks: list[str] = []
        citations: list[Citation] = []
        for i, r in enumerate(selected, start=1):
            payload = r["payload"]
            pid = payload.get("parent_id")
            parent = parents.get(uuid.UUID(pid)) if pid else None
            text = parent.content if parent else payload.get("content", "")
            doc_id = payload.get("document_id")
            doc_name = payload.get("source_name") or "unknown"
            page = payload.get("page")
            chunk_id = payload.get("chunk_id") or r["id"]

            context_blocks.append(f"[{i}] (source: {doc_name}, page: {page})\n{text}")
            citations.append(
                Citation(
                    document_id=uuid.UUID(doc_id) if doc_id else uuid.uuid4(),
                    document_name=doc_name,
                    page=page,
                    chunk_id=uuid.UUID(chunk_id) if self._is_uuid(chunk_id) else uuid.uuid4(),
                    excerpt=(payload.get("content") or "")[:280],
                )
            )

        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Context:\n" + "\n\n".join(context_blocks)
        )
        answer = self.llm.complete(system=SYSTEM_PROMPT, user=user_prompt, large=large)

        # Confidence heuristic: top rerank_score normalized, clipped to [0,1].
        if reranked:
            top = max(r.get("rerank_score", 0.0) for r in reranked)
            confidence = max(0.0, min(1.0, top / 2.0))
        else:
            confidence = 0.0

        return GenerationResult(answer=answer, citations=citations, confidence=confidence)

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError):
            return False


_gen: GenerationService | None = None


def get_generation() -> GenerationService:
    global _gen
    if _gen is None:
        _gen = GenerationService()
    return _gen
