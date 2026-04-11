"""Shared retrieval pipeline used by chat, stream, and evaluation endpoints.

Encapsulates: query expansion → hybrid search → dedup → rerank.
Single source of truth — no duplication across routes.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.query_expansion_service import get_query_expansion
from app.services.rerank_service import get_reranker
from app.services.retrieval_service import get_retrieval

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Output of the retrieval pipeline, ready for generation."""

    reranked: list[dict[str, Any]]
    candidates: list[dict[str, Any]]
    expanded_queries: list[str]
    timings: PipelineTimings


@dataclass
class PipelineTimings:
    embed_ms: int = 0
    search_ms: int = 0
    rerank_ms: int = 0
    rerank_cache_hit: bool = False


def run_retrieval_pipeline(
    query: str,
    tenant_id: uuid.UUID,
    allowed_roles: list[str],
    *,
    mode: str = "standard",
    tag_filters: list[str] | None = None,
    expansion_count: int | None = None,
    retrieval_top_k: int | None = None,
) -> PipelineResult:
    """Execute the full retrieval pipeline.

    Steps:
        1. Query decomposition (deep mode only)
        2. Query expansion via LLM
        3. Hybrid search (dense + sparse) per query variant
        4. Dedup by chunk ID, keep max score
        5. Rerank with Cohere/Voyage

    Returns a PipelineResult with reranked candidates and timing data.
    """
    retrieval = get_retrieval()
    reranker = get_reranker()
    expander = get_query_expansion()

    # Lazy import to avoid circular dependency.
    from app.services.query_router_service import decompose

    # 1. Decompose + expand queries.
    n_expand = expansion_count or settings.query_expansion_count
    top_k = retrieval_top_k or settings.retrieval_top_k

    queries = decompose(query) if mode == "deep" else [query]
    expanded = expander.expand(query, n=n_expand)
    all_queries = queries + expanded

    # 2. Hybrid search.
    t_embed = time.time()
    retrieved_all: list[dict[str, Any]] = []
    for q in all_queries:
        for chunk in retrieval.retrieve(
            query=q,
            tenant_id=tenant_id,
            allowed_roles=allowed_roles,
            tag_filters=tag_filters,
            top_k=top_k,
        ):
            retrieved_all.append({
                "id": chunk.id,
                "score": chunk.score,
                "payload": chunk.payload,
            })
    t_search = time.time()

    # 3. Dedup by ID, keep max score.
    dedup: dict[str, dict[str, Any]] = {}
    for r in retrieved_all:
        existing = dedup.get(r["id"])
        if existing is None or r["score"] > existing["score"]:
            dedup[r["id"]] = r
    candidates = sorted(
        dedup.values(), key=lambda x: x["score"], reverse=True,
    )[:top_k]

    # 4. Rerank.
    t_rerank = time.time()
    reranked = reranker.rerank(query, candidates)[: settings.rerank_top_k]
    t_rerank_end = time.time()

    timings = PipelineTimings(
        embed_ms=int((t_search - t_embed) * 1000),
        search_ms=int((t_rerank - t_search) * 1000),
        rerank_ms=int((t_rerank_end - t_rerank) * 1000),
        rerank_cache_hit=reranker.last_cache_hit,
    )

    return PipelineResult(
        reranked=reranked,
        candidates=candidates,
        expanded_queries=expanded,
        timings=timings,
    )
