"""Worker-side embedder.

Mirrors apps/api/app/services/embedding_service.py exactly so that chunks
indexed by the worker are retrievable by the API with the same hashing scheme
for sparse vectors.

Production: Voyage AI dense + local TF-hash sparse.
Dev fallback: deterministic hash-based pseudo-embedding when VOYAGE_API_KEY
is empty.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Literal

import httpx
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

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


def _unique_token_indices(text: str) -> set[int]:
    """Return the set of hashed sparse indices present in the text."""
    tokens = _tokenize(text)
    return {
        int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16) % _SPARSE_VOCAB_SIZE
        for tok in tokens
    }


def _fallback_dense(text: str, dim: int) -> list[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    i = 0
    while len(out) < dim:
        out.append((h[i % len(h)] / 255.0) * 2.0 - 1.0)
        i += 1
    norm = sum(x * x for x in out) ** 0.5 or 1.0
    return [x / norm for x in out]


class Embedder:
    VOYAGE_ENDPOINT = "https://api.voyageai.com/v1/embeddings"
    BATCH_SIZE = 32

    def __init__(self) -> None:
        self.dim = settings.embedding_dim
        self.model_name = settings.embedding_model
        self.api_key = settings.voyage_api_key
        self.provider = settings.embedding_provider
        self._idf_service = None
        if settings.idf_enabled:
            from app.services.idf_service import get_idf_service
            self._idf_service = get_idf_service()

    def _is_voyage_configured(self) -> bool:
        return self.provider == "voyage" and bool(self.api_key)

    def embed_dense(self, text: str) -> list[float]:
        return self.embed_dense_batch([text])[0]

    def embed_dense_batch(
        self, texts: list[str], *, input_type: InputType = "document"
    ) -> list[list[float]]:
        if not texts:
            return []
        if not self._is_voyage_configured():
            log.warning("embedder.fallback_used", reason="voyage_not_configured")
            return [_fallback_dense(t, self.dim) for t in texts]

        out: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[start : start + self.BATCH_SIZE]
            try:
                resp = httpx.post(
                    self.VOYAGE_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "input": batch,
                        "input_type": input_type,
                    },
                    timeout=120.0,
                )
                resp.raise_for_status()
                data = resp.json()
                out.extend(item["embedding"] for item in data["data"])
            except Exception as e:
                log.error(
                    "embedder.voyage_call_failed",
                    error=str(e),
                    model=self.model_name,
                    batch_size=len(batch),
                )
                out.extend(_fallback_dense(t, self.dim) for t in batch)
        return out

    def embed_sparse(self, text: str) -> dict[str, list]:
        idf_table = self._idf_service.get_idf_table() if self._idf_service else None
        return _sparse_from_text(text, idf_table=idf_table)

    def update_idf_stats(self, text: str) -> None:
        """Update corpus DF counts for the unique tokens in *text*."""
        if self._idf_service:
            try:
                self._idf_service.update_from_document(_unique_token_indices(text))
            except Exception:
                log.warning("embedder.idf_update_failed")


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
