"""Reranker.

Production: Voyage AI rerank-2-lite (or rerank-2 for higher quality at higher cost).
Dev fallback: lexical token overlap, used when VOYAGE_API_KEY is empty so the
platform still answers queries without credentials.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _lexical_overlap_score(query: str, text: str) -> float:
    q_tokens = {t.lower() for t in query.split() if len(t) > 2}
    if not q_tokens:
        return 0.0
    c_tokens = {t.lower() for t in text.split() if len(t) > 2}
    return len(q_tokens & c_tokens) / max(len(q_tokens), 1)


class RerankService:
    VOYAGE_ENDPOINT = "https://api.voyageai.com/v1/rerank"

    def __init__(self) -> None:
        self.model_name = settings.reranker_model
        self.api_key = settings.voyage_api_key
        self.provider = settings.reranker_provider

    def _is_voyage_configured(self) -> bool:
        return self.provider == "voyage" and bool(self.api_key)

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []

        if not self._is_voyage_configured():
            return self._lexical_rerank(query, candidates)

        documents = [(c.get("payload") or {}).get("content", "") for c in candidates]
        try:
            resp = httpx.post(
                self.VOYAGE_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "documents": documents,
                    "model": self.model_name,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            results = resp.json().get("data", [])
            scored: list[dict] = []
            for item in results:
                idx = item["index"]
                score = item["relevance_score"]
                scored.append({**candidates[idx], "rerank_score": score})
            scored.sort(key=lambda x: x["rerank_score"], reverse=True)
            return scored
        except Exception as e:
            log.error("rerank.voyage_call_failed", error=str(e), model=self.model_name)
            return self._lexical_rerank(query, candidates)

    @staticmethod
    def _lexical_rerank(query: str, candidates: list[dict]) -> list[dict]:
        scored = []
        for c in candidates:
            text = (c.get("payload") or {}).get("content", "")
            base = float(c.get("score") or 0.0)
            overlap = _lexical_overlap_score(query, text)
            scored.append({**c, "rerank_score": base * (1.0 + overlap)})
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored


_reranker: RerankService | None = None


def get_reranker() -> RerankService:
    global _reranker
    if _reranker is None:
        _reranker = RerankService()
    return _reranker
