"""Tests for the embedding cache in EmbeddingService."""
from __future__ import annotations

import json
from unittest.mock import patch

import fakeredis

from app.services.embedding_service import EmbeddingService


def _make_service(*, cache_enabled: bool = True) -> EmbeddingService:
    svc = EmbeddingService.__new__(EmbeddingService)
    svc.dim = 4
    svc.model_name = "test"
    svc.api_key = ""
    svc.provider = "fallback"
    svc._idf_table = {}
    svc._idf_ts = 0.0
    svc._redis = fakeredis.FakeRedis(decode_responses=True) if cache_enabled else None
    svc._cache_ttl = 60
    svc._cache_enabled = cache_enabled
    return svc


class TestEmbeddingCache:
    def test_first_call_misses_cache(self) -> None:
        svc = _make_service()
        result = svc.embed("hello", input_type="query")
        assert result["cache_hit"] is False
        assert "dense" in result
        assert "sparse" in result

    def test_second_call_hits_cache(self) -> None:
        svc = _make_service()
        r1 = svc.embed("hello", input_type="query")
        r2 = svc.embed("hello", input_type="query")
        assert r1["cache_hit"] is False
        assert r2["cache_hit"] is True
        assert r1["dense"] == r2["dense"]

    def test_different_queries_different_cache(self) -> None:
        svc = _make_service()
        svc.embed("hello", input_type="query")
        r2 = svc.embed("world", input_type="query")
        assert r2["cache_hit"] is False

    def test_cache_disabled(self) -> None:
        svc = _make_service(cache_enabled=False)
        r1 = svc.embed("hello", input_type="query")
        r2 = svc.embed("hello", input_type="query")
        assert r1["cache_hit"] is False
        assert r2["cache_hit"] is False

    def test_redis_failure_degrades_gracefully(self) -> None:
        svc = _make_service()
        svc._redis = None  # simulate Redis down
        result = svc.embed("hello", input_type="query")
        assert result["cache_hit"] is False
        assert "dense" in result
