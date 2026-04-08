"""Simple offline evaluation harness.

Each `EvaluationCase` gets scored by running the RAG pipeline and comparing
against an expected answer.  Scoring is deliberately lightweight so the
platform boots without extra ML models; replace with RAGAS / LLM-as-judge in
production.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.evaluation import EvaluationCase, EvaluationRun


@dataclass
class CaseResult:
    question: str
    expected: str
    actual: str
    score: float


class EvaluationService:
    def score_lexical(self, expected: str, actual: str) -> float:
        e = {t.lower() for t in expected.split() if len(t) > 2}
        a = {t.lower() for t in actual.split() if len(t) > 2}
        if not e:
            return 0.0
        return len(e & a) / len(e)

    def record_run(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        name: str,
        config: dict,
        results: list[CaseResult],
    ) -> EvaluationRun:
        run = EvaluationRun(
            tenant_id=tenant_id,
            name=name,
            config=config,
            metrics={"mean_score": sum(r.score for r in results) / max(len(results), 1)},
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
                )
            )
        db.commit()
        db.refresh(run)
        return run
