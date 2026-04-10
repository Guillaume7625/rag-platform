"""Embedding service.

Production: dense vectors come from Voyage AI (voyage-3 by default).
Voyage only ships dense embeddings, so the sparse vector used by the hybrid
Qdrant query is computed locally with a lightweight TF + token-hash scheme
weighted by corpus IDF when available.

Dev fallback: if VOYAGE_API_KEY is empty, fall back to a deterministic
hash-based pseudo-embedding so the platform still boots without credentials.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
_SPARSE_VOCAB_SIZE = 100_000

InputType = Literal["document", "query"]


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 1]


def _sparse_from_text(
    text: str, idf_table: dict[int, float] | None = None,
) -> dict[str, list]:
    tokens = _tokenize(text)
    if not tokens:
        return {"indices": [], "values": []}
    counts: Counter[int] = Counter()
    for tok in tokens:
        idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16) % _SPARSE_VOCAB_SIZE
        counts[idx] += 1
    n = len(tokens)
    indices = list(counts.keys())
    # TF * IDF when available; falls back to TF-only (idf=1.0) otherwise.
    idf = idf_table or {}
    values = [(1.0 + (counts[i] / n)) * idf.get(i, 1.0) for i in indices]
    return {"indices": indices, "values": values}


def _fallback_dense(text: str, dim: int) -> list[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    i = 0
    while len(out) < dim:
        out.append((h[i % len(h)] / 255.0) * 2.0 - 1.0)
        i += 1
    norm = sum(x * x for x in out) ** 0.5 or 1.0
    return [x / norm for x in out]


class EmbeddingService:
    """Voyage AI embeddings + lightweight local sparse vectors."""

    VOYAGE_ENDPOINT = "https://api.voyageai.com/v1/embeddings"

    def __init__(self) -> None:
        self.dim = settings.embedding_dim
        self.model_name = settings.embedding_model
        self.api_key = settings.voyage_api_key
        self.provider = settings.embedding_provider
        self._idf_table: dict[int, float] = {}
        self._idf_ts: float = 0.0
        self._redis = None
        self._cache_ttl = settings.embedding_cache_ttl
        self._cache_enabled = settings.embedding_cache_enabled
        if settings.idf_enabled or self._cache_enabled:
            try:
                import redis as _redis
                self._redis = _redis.Redis.from_url(
                    settings.redis_url, decode_responses=True,
                )
            except Exception:
                log.warning("embedding.redis_init_failed")

    def _is_voyage_configured(self) -> bool:
        return self.provider == "voyage" and bool(self.api_key)

    def embed_dense(self, text: str, *, input_type: InputType = "document") -> list[float]:
        return self.embed_dense_batch([text], input_type=input_type)[0]

    def embed_dense_batch(
        self, texts: list[str], *, input_type: InputType = "document"
    ) -> list[list[float]]:
        if not texts:
            return []
        if not self._is_voyage_configured():
            log.warning("embedding.fallback_used", reason="voyage_not_configured")
            return [_fallback_dense(t, self.dim) for t in texts]
        try:
            resp = httpx.post(
                self.VOYAGE_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "input": texts,
                    "input_type": input_type,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            log.error("embedding.voyage_call_failed", error=str(e), model=self.model_name)
            return [_fallback_dense(t, self.dim) for t in texts]

    def _get_idf_table(self) -> dict[int, float] | None:
        """Read-only IDF table from Redis, cached 300s in-process."""
        if not self._redis:
            return None
        import time
        now = time.monotonic()
        if self._idf_table and (now - self._idf_ts) < 300:
            return self._idf_table
        try:
            raw = self._redis.hgetall("idf:global")
            self._idf_table = {int(k): float(v) for k, v in raw.items()}
            self._idf_ts = now
        except Exception:
            log.warning("embedding.idf_read_failed")
        return self._idf_table or None

    def embed_sparse(self, text: str) -> dict[str, list]:
        return _sparse_from_text(text, idf_table=self._get_idf_table())

    def embed(self, text: str, *, input_type: InputType = "document") -> dict[str, Any]:
        if self._cache_enabled and self._redis:
            cache_key = f"emb:{hashlib.sha256((text + '|' + input_type).encode()).hexdigest()[:32]}"
            try:
                cached = self._redis.get(cache_key)
                if cached:
                    result = json.loads(cached)
                    result["cache_hit"] = True
                    return result
            except Exception:
                pass

        result = {
            "dense": self.embed_dense(text, input_type=input_type),
            "sparse": self.embed_sparse(text),
        }

        if self._cache_enabled and self._redis:
            try:
                self._redis.setex(
                    cache_key, self._cache_ttl, json.dumps(result),
                )
            except Exception:
                pass

        result["cache_hit"] = False
        return result


_embedder: EmbeddingService | None = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder
