"""Tests for RAGAS-style evaluation metrics."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.evaluation_service import EvaluationService


def _make_service() -> EvaluationService:
    svc = EvaluationService.__new__(EvaluationService)
    svc.llm = MagicMock()
    return svc


class TestRetrievalRecall:
    def test_perfect_recall(self) -> None:
        assert EvaluationService.score_retrieval_recall_at_k(
            ["a", "b", "c"], ["a", "b"], k=3,
        ) == 1.0

    def test_partial_recall(self) -> None:
        assert EvaluationService.score_retrieval_recall_at_k(
            ["a", "b", "c"], ["a", "d"], k=3,
        ) == 0.5

    def test_zero_recall(self) -> None:
        assert EvaluationService.score_retrieval_recall_at_k(
            ["a", "b"], ["x", "y"], k=2,
        ) == 0.0

    def test_empty_gold(self) -> None:
        assert EvaluationService.score_retrieval_recall_at_k(
            ["a"], [], k=1,
        ) == 0.0

    def test_k_limits_retrieved(self) -> None:
        # Gold "c" is at position 3 but k=2
        assert EvaluationService.score_retrieval_recall_at_k(
            ["a", "b", "c"], ["c"], k=2,
        ) == 0.0


class TestCitationPrecision:
    def test_perfect_precision(self) -> None:
        assert EvaluationService.score_citation_precision(["a", "b"], ["a", "b"]) == 1.0

    def test_partial_precision(self) -> None:
        assert EvaluationService.score_citation_precision(["a", "x"], ["a", "b"]) == 0.5

    def test_empty_cited(self) -> None:
        assert EvaluationService.score_citation_precision([], ["a"]) == 0.0


class TestAnswerRelevance:
    def test_returns_llm_score(self) -> None:
        svc = _make_service()
        svc.llm.complete.return_value = "0.85"
        assert svc.score_answer_relevance("q", "a") == 0.85

    def test_clamps_to_range(self) -> None:
        svc = _make_service()
        svc.llm.complete.return_value = "1.5"
        assert svc.score_answer_relevance("q", "a") == 1.0

    def test_graceful_on_error(self) -> None:
        svc = _make_service()
        svc.llm.complete.side_effect = RuntimeError("down")
        assert svc.score_answer_relevance("q", "a") == 0.0


class TestFaithfulness:
    def test_returns_llm_score(self) -> None:
        svc = _make_service()
        svc.llm.complete.return_value = "0.9"
        assert svc.score_faithfulness("answer", "context") == 0.9


class TestLLMJudge:
    def test_parses_json(self) -> None:
        svc = _make_service()
        svc.llm.complete.return_value = '{"score": 0.75, "explanation": "good"}'
        score, explanation = svc.score_llm_judge("q", "exp", "act", "ctx")
        assert score == 0.75
        assert explanation == "good"

    def test_graceful_on_bad_json(self) -> None:
        svc = _make_service()
        svc.llm.complete.return_value = "not json"
        score, explanation = svc.score_llm_judge("q", "exp", "act", "ctx")
        assert score == 0.0
        assert explanation == "parse_error"
