"""Tests for reranker caching."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import fakeredis
import pytest

from app.services.rerank_service import RerankService


def _make_service(provider: str = "lexical") -> RerankService:
    svc = RerankService.__new__(RerankService)
    svc.model_name = "rerank-2-lite" if provider == "voyage" else "rerank-v3.5"
    svc.api_key = "" if provider == "lexical" else "test-key"
    svc.provider = provider
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

    @pytest.mark.parametrize("provider", ["voyage", "cohere"])
    def test_cache_stores_and_retrieves(self, provider) -> None:
        svc = _make_service(provider)

        # Pre-populate cache.
        cands = _candidates()
        key = svc._cache_key("hello", cands)
        cached = [{"id": "a", "rerank_score": 0.9}, {"id": "b", "rerank_score": 0.3}]
        svc._redis.setex(key, 60, json.dumps(cached))

        result = svc.rerank("hello", cands)
        assert svc.last_cache_hit is True
        assert result == cached


class TestCohereProvider:
    def test_api_call_dispatches_to_cohere(self) -> None:
        svc = _make_service("cohere")
        with patch.object(svc, "_cohere_call", return_value=[]) as mock:
            svc._api_call("query", [])
            mock.assert_called_once()

    def test_api_call_dispatches_to_voyage(self) -> None:
        svc = _make_service("voyage")
        with patch.object(svc, "_voyage_call", return_value=[]) as mock:
            svc._api_call("query", [])
            mock.assert_called_once()

    @patch("httpx.post")
    def test_cohere_call_parses_response(self, mock_post) -> None:
        svc = _make_service("cohere")
        cands = _candidates()
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "results": [
                    {"index": 0, "relevance_score": 0.95},
                    {"index": 1, "relevance_score": 0.3},
                ]
            },
        )
        result = svc._cohere_call("hello", cands)
        assert len(result) == 2
        assert result[0]["rerank_score"] == 0.95
        assert result[0]["id"] == "a"
        # Verify Cohere endpoint was called.
        call_args = mock_post.call_args
        assert "cohere.com" in call_args[0][0]
        assert call_args[1]["json"]["model"] == "rerank-v3.5"
