"""Tests for dynamic context sizing in GenerationService."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.services.generation_service import GenerationService


def _make_reranked(n: int, token_count: int = 200) -> list[dict]:
    return [
        {
            "id": str(i),
            "payload": {"parent_id": str(uuid.uuid4())},
            "rerank_score": 1.0 - i * 0.1,
        }
        for i in range(n)
    ]


class TestDynamicContext:
    def test_budget_limits_parents(self) -> None:
        svc = GenerationService.__new__(GenerationService)
        db = MagicMock()
        # Each parent has 1500 tokens; budget=4000 fits 2 (3rd would exceed).
        db.query.return_value.filter.return_value.first.return_value = (1500,)

        reranked = _make_reranked(5)
        with patch("app.services.generation_service.settings") as s:
            s.context_token_budget = 4000
            s.context_score_threshold = 0.0
            s.context_max_parents = 10
            result = svc._select_context(reranked, db)

        assert len(result) == 2

    def test_score_threshold_cuts_off(self) -> None:
        svc = GenerationService.__new__(GenerationService)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = (100,)

        reranked = _make_reranked(5)
        # Only first 2 have score >= 0.85
        with patch("app.services.generation_service.settings") as s:
            s.context_token_budget = 100000
            s.context_score_threshold = 0.85
            s.context_max_parents = 10
            result = svc._select_context(reranked, db)

        assert len(result) == 2  # scores 1.0 and 0.9

    def test_always_includes_at_least_one(self) -> None:
        svc = GenerationService.__new__(GenerationService)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = (9999,)

        reranked = _make_reranked(3)
        with patch("app.services.generation_service.settings") as s:
            s.context_token_budget = 100  # way under
            s.context_score_threshold = 0.0
            s.context_max_parents = 10
            result = svc._select_context(reranked, db)

        assert len(result) == 1

    def test_dedup_by_parent_id(self) -> None:
        svc = GenerationService.__new__(GenerationService)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = (100,)

        pid = str(uuid.uuid4())
        reranked = [
            {"id": "1", "payload": {"parent_id": pid}, "rerank_score": 0.9},
            {"id": "2", "payload": {"parent_id": pid}, "rerank_score": 0.8},
        ]
        with patch("app.services.generation_service.settings") as s:
            s.context_token_budget = 100000
            s.context_score_threshold = 0.0
            s.context_max_parents = 10
            result = svc._select_context(reranked, db)

        assert len(result) == 1
