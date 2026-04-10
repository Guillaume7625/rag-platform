"""Reranker.

Production: Voyage AI rerank-2-lite (or rerank-2 for higher quality at higher cost).
Features a Redis cache and two-pass early stopping to reduce API costs.
Dev fallback: lexical token overlap, used when VOYAGE_API_KEY is empty so the
platform still answers queries without credentials.
"""
from __future__ import annotations

import hashlib
import json

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
        self.last_cache_hit: bool = False
        self._redis = None
        if settings.rerank_cache_enabled:
            try:
                import redis as _redis
                self._redis = _redis.Redis.from_url(
                    settings.redis_url, decode_responses=True,
                )
            except Exception:
                log.warning("rerank.redis_init_failed")

    def _is_voyage_configured(self) -> bool:
        return self.provider == "voyage" and bool(self.api_key)

    def _cache_key(self, query: str, candidates: list[dict]) -> str:
        ids = sorted(str(c.get("id", "")) for c in candidates)
        raw = query + "|" + ",".join(ids)
        return f"rerank:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"

    def _voyage_call(self, query: str, candidates: list[dict]) -> list[dict]:
        """Call Voyage rerank API for a subset of candidates."""
        documents = [(c.get("payload") or {}).get("content", "") for c in candidates]
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
        return scored

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []

        self.last_cache_hit = False

        if not self._is_voyage_configured():
            return self._lexical_rerank(query, candidates)

        # Check cache.
        if self._redis and settings.rerank_cache_enabled:
            cache_key = self._cache_key(query, candidates)
            try:
                cached = self._redis.get(cache_key)
                if cached:
                    self.last_cache_hit = True
                    return json.loads(cached)
            except Exception:
                pass

        try:
            # Two-pass early stopping: rerank first N, skip rest if confident.
            first_pass_size = min(settings.rerank_first_pass_size, len(candidates))
            first_pass = self._voyage_call(query, candidates[:first_pass_size])
            first_pass.sort(key=lambda x: x["rerank_score"], reverse=True)

            threshold = settings.rerank_early_stop_threshold
            if (
                len(first_pass) >= 2
                and first_pass[0]["rerank_score"] > threshold
                and first_pass[0]["rerank_score"] > 2 * first_pass[1]["rerank_score"]
            ):
                log.info("rerank.early_stop", top_score=first_pass[0]["rerank_score"])
                scored = first_pass
            elif first_pass_size < len(candidates):
                second_pass = self._voyage_call(query, candidates[first_pass_size:])
                scored = first_pass + second_pass
                scored.sort(key=lambda x: x["rerank_score"], reverse=True)
            else:
                scored = first_pass

            # Cache result.
            if self._redis and settings.rerank_cache_enabled:
                try:
                    self._redis.setex(
                        cache_key, settings.rerank_cache_ttl, json.dumps(scored),
                    )
                except Exception:
                    pass

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
