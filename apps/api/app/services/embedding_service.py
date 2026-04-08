"""Embedding service.

Production: dense vectors come from Voyage AI (voyage-3 by default).
Voyage only ships dense embeddings, so the sparse vector used by the hybrid
Qdrant query is computed locally with a lightweight TF + token-hash scheme.
It is not full BM25 (no global IDF), but it captures keyword overlap and is
cheap, deterministic, and identical between API and worker.

Dev fallback: if VOYAGE_API_KEY is empty, fall back to a deterministic
hash-based pseudo-embedding so the platform still boots without credentials.
"""
from __future__ import annotations

import hashlib
import re
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


def _sparse_from_text(text: str) -> dict[str, list]:
    tokens = _tokenize(text)
    if not tokens:
        return {"indices": [], "values": []}
    counts: Counter[int] = Counter()
    for tok in tokens:
        idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16) % _SPARSE_VOCAB_SIZE
        counts[idx] += 1
    n = len(tokens)
    indices = list(counts.keys())
    # Log-tf normalization. Real BM25 would multiply by IDF (corpus stats).
    values = [1.0 + (counts[i] / n) for i in indices]
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

    def embed_sparse(self, text: str) -> dict[str, list]:
        return _sparse_from_text(text)

    def embed(self, text: str, *, input_type: InputType = "document") -> dict[str, Any]:
        return {
            "dense": self.embed_dense(text, input_type=input_type),
            "sparse": self.embed_sparse(text),
        }


_embedder: EmbeddingService | None = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder
