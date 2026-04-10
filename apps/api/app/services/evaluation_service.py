"""Offline evaluation harness with RAGAS-style metrics and LLM-as-judge.

Metrics:
- score_lexical: token-overlap baseline
- score_retrieval_recall_at_k: fraction of gold chunks in top-k retrieved
- score_citation_precision: fraction of cited documents that are in the gold set
- score_answer_relevance: LLM-judged relevance (0–1)
- score_faithfulness: LLM-judged faithfulness to context (0–1)
- score_llm_judge: composite LLM scoring with explanation
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models.evaluation import EvaluationCase, EvaluationRun
from app.services.llm_provider import get_llm

log = get_logger(__name__)


@dataclass
class CaseResult:
    question: str
    expected: str
    actual: str
    score: float
    retrieval_recall: float | None = None
    citation_precision: float | None = None
    answer_relevance: float | None = None
    faithfulness: float | None = None
    llm_judge_score: float | None = None
    llm_judge_explanation: str | None = None


class EvaluationService:
    def __init__(self) -> None:
        self.llm = get_llm()

    def score_lexical(self, expected: str, actual: str) -> float:
        e = {t.lower() for t in expected.split() if len(t) > 2}
        a = {t.lower() for t in actual.split() if len(t) > 2}
        if not e:
            return 0.0
        return len(e & a) / len(e)

    @staticmethod
    def score_retrieval_recall_at_k(
        retrieved_ids: list[str], gold_ids: list[str], k: int,
    ) -> float:
        if not gold_ids:
            return 0.0
        return len(set(retrieved_ids[:k]) & set(gold_ids)) / len(gold_ids)

    @staticmethod
    def score_citation_precision(
        cited_doc_ids: list[str], gold_doc_ids: list[str],
    ) -> float:
        if not cited_doc_ids:
            return 0.0
        return len(set(cited_doc_ids) & set(gold_doc_ids)) / len(cited_doc_ids)

    def score_answer_relevance(self, question: str, answer: str) -> float:
        try:
            raw = self.llm.complete(
                system=(
                    "Rate how relevant the following answer is to the question. "
                    "Score from 0.0 to 1.0. Output only the number."
                ),
                user=f"Question: {question}\n\nAnswer: {answer}",
                large=False,
            )
            return max(0.0, min(1.0, float(raw.strip())))
        except Exception:
            return 0.0

    def score_faithfulness(self, answer: str, context: str) -> float:
        try:
            raw = self.llm.complete(
                system=(
                    "Rate how faithfully the answer is supported by the context. "
                    "Score from 0.0 to 1.0. A score of 1.0 means every claim in "
                    "the answer is supported by the context. Output only the number."
                ),
                user=f"Context: {context}\n\nAnswer: {answer}",
                large=False,
            )
            return max(0.0, min(1.0, float(raw.strip())))
        except Exception:
            return 0.0

    def score_llm_judge(
        self, question: str, expected: str, actual: str, context: str,
    ) -> tuple[float, str]:
        try:
            raw = self.llm.complete(
                system=(
                    "You are evaluating a RAG system answer. "
                    'Output a JSON object: {"score": <float 0-1>, "explanation": "<string>"}.'
                ),
                user=(
                    f"Question: {question}\n\n"
                    f"Expected answer: {expected}\n\n"
                    f"Actual answer: {actual}\n\n"
                    f"Context provided: {context}"
                ),
                large=False,
            )
            data = json.loads(raw.strip())
            return (
                max(0.0, min(1.0, float(data["score"]))),
                str(data.get("explanation", "")),
            )
        except Exception:
            return (0.0, "parse_error")

    def record_run(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        name: str,
        config: dict,
        results: list[CaseResult],
    ) -> EvaluationRun:
        def _mean(vals: list[float]) -> float:
            return sum(vals) / max(len(vals), 1)

        metrics = {
            "mean_score": _mean([r.score for r in results]),
        }
        rr = [r.retrieval_recall for r in results if r.retrieval_recall is not None]
        if rr:
            metrics["mean_retrieval_recall"] = _mean(rr)
        cp = [r.citation_precision for r in results if r.citation_precision is not None]
        if cp:
            metrics["mean_citation_precision"] = _mean(cp)
        ar = [r.answer_relevance for r in results if r.answer_relevance is not None]
        if ar:
            metrics["mean_answer_relevance"] = _mean(ar)
        ff = [r.faithfulness for r in results if r.faithfulness is not None]
        if ff:
            metrics["mean_faithfulness"] = _mean(ff)

        run = EvaluationRun(
            tenant_id=tenant_id,
            name=name,
            config=config,
            metrics=metrics,
        )
        db.add(run)
        db.flush()
        for r in results:
            db.add(
                EvaluationCase(
                    run_id=run.id,
                    question=r.question,
                    expected=r.expected,
                    actual=r.actual,
                    score=r.score,
                    details={
                        "retrieval_recall": r.retrieval_recall,
                        "citation_precision": r.citation_precision,
                        "answer_relevance": r.answer_relevance,
                        "faithfulness": r.faithfulness,
                        "llm_judge_score": r.llm_judge_score,
                        "llm_judge_explanation": r.llm_judge_explanation,
                    },
                )
            )
        db.commit()
        db.refresh(run)
        return run


_eval: EvaluationService | None = None


def get_evaluation() -> EvaluationService:
    global _eval
    if _eval is None:
        _eval = EvaluationService()
    return _eval
