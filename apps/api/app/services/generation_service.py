"""Generation step: packs context, calls the LLM, produces citations."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.chunk import DocumentChunkParent
from app.schemas.chat import Citation
from app.services.llm_provider import get_llm

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Tu es un assistant précis et rigoureux. Réponds à la question de l'utilisateur "
    "en utilisant UNIQUEMENT le contexte fourni. Cite tes sources avec leur identifiant [n]. "
    "Si plusieurs documents sont fournis dans le contexte, couvre-les tous dans ta réponse. "
    "Si le contexte ne contient pas la réponse, dis que tu ne sais pas."
)


@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation]
    confidence: float


class GenerationService:
    def __init__(self) -> None:
        self.llm = get_llm()

    def _select_context(
        self,
        reranked: list[dict[str, Any]],
        db: Session,
    ) -> list[dict[str, Any]]:
        """Select parent chunks with document diversity (round-robin).

        Instead of picking the top N chunks (which often come from one document),
        we distribute selection across documents: best chunk from each doc first,
        then second-best from each doc, etc. This ensures multi-document coverage
        while still respecting token budget and score thresholds.
        """
        if not reranked:
            return []

        # Group candidates by document_id, preserving rerank order within each doc.
        from collections import OrderedDict

        doc_buckets: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        seen_parents: set[str] = set()
        for r in reranked:
            pid = r["payload"].get("parent_id")
            if pid in seen_parents:
                continue
            seen_parents.add(pid)
            doc_id = r["payload"].get("document_id", "unknown")
            if doc_id not in doc_buckets:
                doc_buckets[doc_id] = []
            doc_buckets[doc_id].append(r)

        # Round-robin: pick one chunk from each document in turn.
        ordered: list[dict[str, Any]] = []
        max_depth = max((len(v) for v in doc_buckets.values()), default=0)
        for depth in range(max_depth):
            for doc_id, chunks in doc_buckets.items():
                if depth < len(chunks):
                    ordered.append(chunks[depth])

        # Fill selected list within budget.
        # Guarantee: at least 1 chunk from each document (diversity first).
        selected: list[dict[str, Any]] = []
        seen_docs_in_selected: set[str] = set()
        budget = settings.context_token_budget
        accumulated = 0

        for r in ordered:
            score = r.get("rerank_score", 0.0)
            doc_id = r["payload"].get("document_id", "unknown")
            doc_already_covered = doc_id in seen_docs_in_selected
            # Only apply score threshold if this doc is already represented
            if doc_already_covered and score < settings.context_score_threshold:
                continue

            pid = r["payload"].get("parent_id")
            token_count = 0
            if pid:
                parent = (
                    db.query(DocumentChunkParent.token_count)
                    .filter(DocumentChunkParent.id == uuid.UUID(pid))
                    .first()
                )
                token_count = parent[0] if parent else 200

            if selected and accumulated + token_count > budget:
                break

            selected.append(r)
            seen_docs_in_selected.add(doc_id)
            accumulated += token_count

            if len(selected) >= settings.context_max_parents:
                break

        return selected

    @staticmethod
    def _compute_confidence(reranked: list[dict[str, Any]]) -> float:
        """3-signal confidence: top score, spread, and high-scoring density."""
        if not reranked:
            return 0.0
        scores = [r.get("rerank_score", 0.0) for r in reranked]
        top_score = max(scores)
        mean_score = sum(scores) / len(scores)
        spread = top_score - mean_score
        high_count = sum(1 for s in scores if s > 0.5 * top_score)
        density = min(high_count, 5) / 5.0
        raw = top_score * 0.5 + spread * 0.3 + density * 0.2
        return max(0.0, min(1.0, raw))

    def pack_and_generate(
        self,
        db: Session,
        query: str,
        reranked: list[dict[str, Any]],
        large: bool = False,
    ) -> GenerationResult:
        # Dynamic context selection within token budget.
        selected = self._select_context(reranked, db)

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

            if not doc_id:
                log.warning("citation.missing_document_id", payload_keys=list(payload.keys()))
                continue
            if not self._is_uuid(chunk_id):
                log.warning("citation.invalid_chunk_id", chunk_id=chunk_id)
                continue

            context_blocks.append(f"[{i}] (source: {doc_name}, page: {page})\n{text}")
            citations.append(
                Citation(
                    document_id=uuid.UUID(doc_id),
                    document_name=doc_name,
                    page=page,
                    chunk_id=uuid.UUID(chunk_id),
                    excerpt=(payload.get("content") or "")[:280],
                )
            )

        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Context:\n" + "\n\n".join(context_blocks)
        )
        answer = self.llm.complete(system=SYSTEM_PROMPT, user=user_prompt, large=large)

        confidence = self._compute_confidence(reranked)

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
