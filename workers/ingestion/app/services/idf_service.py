"""Corpus-level IDF statistics for BM25-style sparse vectors.

Stores document-frequency counts in Redis and computes IDF values used to
weight sparse vector entries.  When IDF is unavailable (empty table or Redis
down), callers fall back to a 1.0 multiplier — identical to the pre-IDF
TF-only behavior.

Redis keys:
    idf:doc_count   — integer, total documents seen
    idf:df          — hash, {sparse_index: document_frequency}
    idf:global      — hash, {sparse_index: idf_value}
"""
from __future__ import annotations

import math
import time

import redis
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

_CACHE_TTL = 300  # seconds


class IDFService:
    def __init__(self, redis_url: str) -> None:
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._cache: dict[int, float] = {}
        self._cache_ts: float = 0.0

    # ------------------------------------------------------------------
    # Write path (worker only)
    # ------------------------------------------------------------------

    def update_from_document(self, token_indices: set[int]) -> None:
        """Increment DF counts for *unique* token indices in one document."""
        pipe = self._redis.pipeline(transaction=False)
        pipe.incr("idf:doc_count")
        for idx in token_indices:
            pipe.hincrby("idf:df", str(idx), 1)
        pipe.execute()

    def rebuild_idf_table(self) -> None:
        """Recompute the global IDF hash from current DF counts."""
        n = int(self._redis.get("idf:doc_count") or 0)
        if n == 0:
            return
        df_raw = self._redis.hgetall("idf:df")
        pipe = self._redis.pipeline(transaction=False)
        pipe.delete("idf:global")
        for idx_str, df_str in df_raw.items():
            df = int(df_str)
            idf = math.log((n + 1) / (df + 1))
            pipe.hset("idf:global", idx_str, str(idf))
        pipe.execute()
        log.info("idf.rebuild_complete", doc_count=n, terms=len(df_raw))

    # ------------------------------------------------------------------
    # Read path (worker + API)
    # ------------------------------------------------------------------

    def get_idf_table(self) -> dict[int, float]:
        """Return the IDF lookup table, cached in-process for up to 300s."""
        now = time.monotonic()
        if self._cache and (now - self._cache_ts) < _CACHE_TTL:
            return self._cache
        try:
            raw = self._redis.hgetall("idf:global")
            self._cache = {int(k): float(v) for k, v in raw.items()}
            self._cache_ts = now
        except Exception:
            log.warning("idf.redis_read_failed")
        return self._cache


_idf: IDFService | None = None


def get_idf_service() -> IDFService:
    global _idf
    if _idf is None:
        _idf = IDFService(settings.redis_url)
    return _idf
