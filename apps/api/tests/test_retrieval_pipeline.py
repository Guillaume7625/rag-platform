"""Tests for the shared retrieval pipeline."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.retrieval_pipeline import PipelineResult, PipelineTimings, run_retrieval_pipeline


class TestRetrievalPipeline:
    @patch("app.services.retrieval_pipeline.get_reranker")
    @patch("app.services.retrieval_pipeline.get_retrieval")
    @patch("app.services.retrieval_pipeline.get_query_expansion")
    def test_pipeline_deduplicates_by_id(self, mock_expand, mock_retrieval, mock_reranker):
        """Duplicate chunk IDs should be deduped, keeping max score."""
        mock_expand.return_value.expand.return_value = []

        chunk1 = MagicMock(id="c1", score=0.9, payload={"content": "text"})
        chunk2 = MagicMock(id="c1", score=0.5, payload={"content": "text"})  # same ID, lower score
        chunk3 = MagicMock(id="c2", score=0.7, payload={"content": "other"})

        mock_retrieval.return_value.retrieve.return_value = [chunk1, chunk2, chunk3]
        mock_reranker.return_value.rerank.side_effect = lambda q, c: c
        mock_reranker.return_value.last_cache_hit = False

        import uuid

        result = run_retrieval_pipeline(
            query="test",
            tenant_id=uuid.uuid4(),
            allowed_roles=["member"],
        )

        # Should have 2 candidates (c1 deduped, c2 unique)
        assert len(result.candidates) == 2
        # c1 should have the higher score
        scores = {c["id"]: c["score"] for c in result.candidates}
        assert scores["c1"] == 0.9

    @patch("app.services.retrieval_pipeline.get_reranker")
    @patch("app.services.retrieval_pipeline.get_retrieval")
    @patch("app.services.retrieval_pipeline.get_query_expansion")
    def test_pipeline_returns_timings(self, mock_expand, mock_retrieval, mock_reranker):
        """Pipeline should return timing information."""
        mock_expand.return_value.expand.return_value = []
        mock_retrieval.return_value.retrieve.return_value = []
        mock_reranker.return_value.rerank.return_value = []
        mock_reranker.return_value.last_cache_hit = False

        import uuid

        result = run_retrieval_pipeline(
            query="test",
            tenant_id=uuid.uuid4(),
            allowed_roles=["member"],
        )

        assert isinstance(result, PipelineResult)
        assert isinstance(result.timings, PipelineTimings)
        assert result.timings.embed_ms >= 0


class TestConfidenceComputation:
    def test_empty_reranked_returns_zero(self):
        from app.services.generation_service import GenerationService

        svc = GenerationService.__new__(GenerationService)
        assert svc.compute_confidence([]) == 0.0

    def test_high_score_gives_high_confidence(self):
        from app.services.generation_service import GenerationService

        svc = GenerationService.__new__(GenerationService)
        reranked = [
            {"rerank_score": 0.95},
            {"rerank_score": 0.3},
            {"rerank_score": 0.1},
        ]
        conf = svc.compute_confidence(reranked)
        assert conf > 0.5

    def test_low_scores_give_low_confidence(self):
        from app.services.generation_service import GenerationService

        svc = GenerationService.__new__(GenerationService)
        reranked = [
            {"rerank_score": 0.1},
            {"rerank_score": 0.08},
        ]
        conf = svc.compute_confidence(reranked)
        assert conf < 0.3


class TestInputValidation:
    def test_query_max_length(self):
        from pydantic import ValidationError

        from app.schemas.chat import ChatQueryRequest

        # Valid
        req = ChatQueryRequest(query="test")
        assert req.query == "test"

        # Too long
        try:
            ChatQueryRequest(query="x" * 2001)
            raise AssertionError("Should have raised")
        except ValidationError:
            pass

    def test_query_empty_rejected(self):
        from pydantic import ValidationError

        from app.schemas.chat import ChatQueryRequest

        try:
            ChatQueryRequest(query="")
            raise AssertionError("Should have raised")
        except ValidationError:
            pass

    def test_force_mode_validation(self):
        from pydantic import ValidationError

        from app.schemas.chat import ChatQueryRequest

        # Valid modes
        ChatQueryRequest(query="test", force_mode="standard")
        ChatQueryRequest(query="test", force_mode="deep")
        ChatQueryRequest(query="test", force_mode=None)

        # Invalid mode
        try:
            ChatQueryRequest(query="test", force_mode="invalid")
            raise AssertionError("Should have raised")
        except ValidationError:
            pass
