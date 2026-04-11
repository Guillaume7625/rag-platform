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

SYSTEM_PROMPT = """\
Tu es un assistant expert en analyse documentaire. Tu travailles pour une organisation \
qui a besoin de r\u00e9ponses pr\u00e9cises, factuelles et bien structur\u00e9es.

## R\u00e8gles absolues
1. R\u00e9ponds UNIQUEMENT \u00e0 partir du contexte fourni. Ne g\u00e9n\u00e8re JAMAIS d'information \
qui n'est pas dans le contexte.
2. Si le contexte ne contient pas assez d'information, dis-le explicitement. \
Ne comble JAMAIS les lacunes avec tes connaissances g\u00e9n\u00e9rales.
3. Chaque affirmation doit \u00eatre cit\u00e9e avec [n] renvoyant \u00e0 la source.

## Format de r\u00e9ponse
- R\u00e9ponds toujours en fran\u00e7ais.
- Utilise des titres markdown (## et ###) pour structurer les r\u00e9ponses longues.
- Utilise des listes \u00e0 puces pour les \u00e9num\u00e9rations.
- Mets en **gras** les termes cl\u00e9s et concepts importants.
- Sois concis : va droit au but sans r\u00e9p\u00e9tition.

## Gestion multi-documents
- Si le contexte contient des extraits de plusieurs documents, synth\u00e9tise une \
r\u00e9ponse crois\u00e9e qui int\u00e8gre les informations de toutes les sources.
- Indique les convergences et divergences entre les sources si pertinent.
- Attribue chaque information \u00e0 sa source sp\u00e9cifique avec [n].

## Ton
- Professionnel et factuel.
- Pas de formules de politesse superflues. Pas de "Bien s\u00fbr !" ni "Excellente question !".
- Commence directement par le contenu."""

CLARIFICATION_PROMPT = """\
Tu es un assistant expert en analyse documentaire.

Le contexte fourni ne couvre pas parfaitement la question pos\u00e9e. Tu dois :

1. **R\u00e9pondre partiellement** avec ce que le contexte contient. Cite avec [n].
2. **Identifier les lacunes** : indique clairement ce qui manque dans les documents \
pour r\u00e9pondre compl\u00e8tement.
3. **Poser 1 \u00e0 2 questions de clarification** pour aider l'utilisateur \u00e0 reformuler \
sa question ou pr\u00e9ciser ce qu'il cherche.

## Format
- R\u00e9ponds en fran\u00e7ais.
- Structure avec des titres markdown.
- Termine par une section :

### \U0001f50d Pour affiner ma recherche
- **Question 1 en gras**
- **Question 2 en gras** (optionnel)

## Ton
- Professionnel et utile. Montre que tu as cherch\u00e9 s\u00e9rieusement.
- Pas de formules de politesse superflues."""


@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation]
    confidence: float


class GenerationService:
    def __init__(self) -> None:
        self.llm = get_llm()

    def select_context(
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
            for _doc_id, chunks in doc_buckets.items():
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
    def compute_confidence(reranked: list[dict[str, Any]]) -> float:
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
        selected = self.select_context(reranked, db)

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

        # Compute confidence BEFORE generating to choose the right prompt.
        confidence = self.compute_confidence(reranked)

        # Use clarification prompt if confidence is low.
        system = CLARIFICATION_PROMPT if confidence < 0.70 else SYSTEM_PROMPT

        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Context:\n" + "\n\n".join(context_blocks)
        )
        answer = self.llm.complete(system=system, user=user_prompt, large=large)

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
