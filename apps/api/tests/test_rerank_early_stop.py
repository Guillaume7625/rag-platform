"""Tests for two-pass early stopping in the reranker."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import fakeredis
import pytest

from app.services.rerank_service import RerankService


def _make_service(provider: str = "voyage") -> RerankService:
    svc = RerankService.__new__(RerankService)
    svc.model_name = "rerank-2-lite" if provider == "voyage" else "rerank-v3.5"
    svc.api_key = "test-key"
    svc.provider = provider
    svc.last_cache_hit = False
    svc._redis = fakeredis.FakeRedis(decode_responses=True)
    return svc


def _candidates(n: int) -> list[dict]:
    return [
        {"id": str(i), "score": 1.0 - i * 0.01, "payload": {"content": f"text {i}"}}
        for i in range(n)
    ]


class TestRerankEarlyStop:
    @pytest.mark.parametrize("provider", ["voyage", "cohere"])
    @patch.object(RerankService, "_api_call")
    def test_early_stop_skips_second_pass(self, mock_call, provider) -> None:
        svc = _make_service(provider)
        cands = _candidates(20)

        # First pass returns a dominant top score.
        mock_call.return_value = [
            {"id": "0", "rerank_score": 0.95, "payload": {"content": "text 0"}},
            {"id": "1", "rerank_score": 0.2, "payload": {"content": "text 1"}},
        ]

        with patch("app.services.rerank_service.settings") as mock_settings:
            mock_settings.rerank_cache_enabled = True
            mock_settings.rerank_cache_ttl = 60
            mock_settings.rerank_first_pass_size = 2
            mock_settings.rerank_early_stop_threshold = 0.85
            mock_settings.redis_url = ""
            result = svc.rerank("query", cands)

        assert mock_call.call_count == 1
        assert result[0]["rerank_score"] == 0.95

    @pytest.mark.parametrize("provider", ["voyage", "cohere"])
    @patch.object(RerankService, "_api_call")
    def test_no_early_stop_calls_second_pass(self, mock_call, provider) -> None:
        svc = _make_service(provider)
        cands = _candidates(20)

        # First pass: scores too close to trigger early stop.
        first = [
            {"id": "0", "rerank_score": 0.6, "payload": {"content": "text 0"}},
            {"id": "1", "rerank_score": 0.5, "payload": {"content": "text 1"}},
        ]
        second = [
            {"id": "2", "rerank_score": 0.7, "payload": {"content": "text 2"}},
        ]
        mock_call.side_effect = [first, second]

        with patch("app.services.rerank_service.settings") as mock_settings:
            mock_settings.rerank_cache_enabled = True
            mock_settings.rerank_cache_ttl = 60
            mock_settings.rerank_first_pass_size = 2
            mock_settings.rerank_early_stop_threshold = 0.85
            mock_settings.redis_url = ""
            result = svc.rerank("query", cands)

        assert mock_call.call_count == 2
        assert result[0]["rerank_score"] == 0.7  # second pass had the best
