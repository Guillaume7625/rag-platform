"""Tests for query expansion service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.query_expansion_service import QueryExpansionService


class TestQueryExpansion:
    def test_expand_returns_reformulations(self) -> None:
        svc = QueryExpansionService.__new__(QueryExpansionService)
        svc.llm = MagicMock()
        svc.llm.complete.return_value = "What is RAG?\nHow does RAG work?"

        with patch("app.services.query_expansion_service.settings") as s:
            s.query_expansion_enabled = True
            result = svc.expand("explain RAG", n=2)

        assert result == ["What is RAG?", "How does RAG work?"]

    def test_expand_limits_to_n(self) -> None:
        svc = QueryExpansionService.__new__(QueryExpansionService)
        svc.llm = MagicMock()
        svc.llm.complete.return_value = "A\nB\nC\nD"

        with patch("app.services.query_expansion_service.settings") as s:
            s.query_expansion_enabled = True
            result = svc.expand("test", n=2)

        assert len(result) == 2

    def test_expand_graceful_on_failure(self) -> None:
        svc = QueryExpansionService.__new__(QueryExpansionService)
        svc.llm = MagicMock()
        svc.llm.complete.side_effect = RuntimeError("API down")

        with patch("app.services.query_expansion_service.settings") as s:
            s.query_expansion_enabled = True
            result = svc.expand("test", n=2)

        assert result == []

    def test_expand_disabled(self) -> None:
        svc = QueryExpansionService.__new__(QueryExpansionService)
        svc.llm = MagicMock()

        with patch("app.services.query_expansion_service.settings") as s:
            s.query_expansion_enabled = False
            result = svc.expand("test", n=2)

        assert result == []
        svc.llm.complete.assert_not_called()
