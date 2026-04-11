"""Tests for confidence calibration."""
from __future__ import annotations

from app.services.generation_service import GenerationService


class TestConfidence:
    def test_empty_reranked(self) -> None:
        assert GenerationService.compute_confidence([]) == 0.0

    def test_single_high_score(self) -> None:
        reranked = [{"rerank_score": 0.0}] * 9 + [{"rerank_score": 0.95}]
        c = GenerationService.compute_confidence(reranked)
        assert 0.0 <= c <= 1.0
        assert c > 0.4

    def test_all_zero_scores(self) -> None:
        reranked = [{"rerank_score": 0.0}] * 5
        c = GenerationService.compute_confidence(reranked)
        assert c == 0.0

    def test_all_similar_moderate(self) -> None:
        reranked = [{"rerank_score": 0.5}] * 5
        c = GenerationService.compute_confidence(reranked)
        assert 0.0 <= c <= 1.0

    def test_result_always_in_range(self) -> None:
        reranked = [{"rerank_score": 2.0}] * 10  # artificially high
        c = GenerationService.compute_confidence(reranked)
        assert 0.0 <= c <= 1.0
