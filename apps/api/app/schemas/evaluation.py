"""Schemas for the evaluation endpoint."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EvalCaseInput(BaseModel):
    question: str
    expected: str
    gold_chunk_ids: list[str] | None = None
    gold_doc_ids: list[str] | None = None


class EvalRunRequest(BaseModel):
    name: str
    cases: list[EvalCaseInput]


class EvalCaseResult(BaseModel):
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


class EvalRunResponse(BaseModel):
    run_id: uuid.UUID
    name: str
    metrics: dict[str, Any]
    cases: list[EvalCaseResult]


class EvalRunSummary(BaseModel):
    run_id: uuid.UUID
    name: str | None
    metrics: dict[str, Any] | None
    created_at: datetime | None
