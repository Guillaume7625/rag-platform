"""Tests for reranker caching."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import fakeredis

from app.services.rerank_service import RerankService


def _make_service() -> RerankService:
    svc = RerankService.__new__(RerankService)
    svc.model_name = "rerank-2-lite"
    svc.api_key = ""
    svc.provider = "lexical"
    svc.last_cache_hit = False
    svc._redis = fakeredis.FakeRedis(decode_responses=True)
    return svc


def _candidates() -> list[dict]:
    return [
        {"id": "a", "score": 0.9, "payload": {"content": "hello world"}},
        {"id": "b", "score": 0.5, "payload": {"content": "foo bar"}},
    ]


class TestRerankCache:
    def test_lexical_rerank_no_cache(self) -> None:
        svc = _make_service()
        result = svc.rerank("hello", _candidates())
        assert len(result) == 2
        assert svc.last_cache_hit is False

    def test_cache_stores_and_retrieves(self) -> None:
        svc = _make_service()
        svc.provider = "voyage"
        svc.api_key = "test-key"

        # Pre-populate cache.
        cands = _candidates()
        key = svc._cache_key("hello", cands)
        cached = [{"id": "a", "rerank_score": 0.9}, {"id": "b", "rerank_score": 0.3}]
        svc._redis.setex(key, 60, json.dumps(cached))

        result = svc.rerank("hello", cands)
        assert svc.last_cache_hit is True
        assert result == cached
