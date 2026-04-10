"""Evaluation endpoint — trigger eval runs and view results."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.db.models.evaluation import EvaluationRun
from app.db.session import get_db
from app.schemas.evaluation import (
    EvalCaseResult,
    EvalRunRequest,
    EvalRunResponse,
    EvalRunSummary,
)
from app.services.evaluation_service import CaseResult, get_evaluation
from app.services.generation_service import get_generation
from app.services.query_router_service import decide_mode, decompose
from app.services.rerank_service import get_reranker
from app.services.retrieval_service import get_retrieval

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.post("/run", response_model=EvalRunResponse)
def run_evaluation(
    payload: EvalRunRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvalRunResponse:
    eval_svc = get_evaluation()
    retrieval = get_retrieval()
    reranker = get_reranker()
    generator = get_generation()

    results: list[CaseResult] = []
    case_outputs: list[EvalCaseResult] = []

    for case in payload.cases:
        mode = decide_mode(case.question)
        queries = decompose(case.question) if mode == "deep" else [case.question]
        retrieved_all: list[dict] = []
        for q in queries:
            for c in retrieval.retrieve(
                query=q,
                tenant_id=current.tenant_id,
                allowed_roles=current.allowed_roles,
            ):
                retrieved_all.append({"id": c.id, "score": c.score, "payload": c.payload})

        dedup: dict[str, dict] = {}
        for r in retrieved_all:
            cur = dedup.get(r["id"])
            if cur is None or r["score"] > cur["score"]:
                dedup[r["id"]] = r
        candidates = sorted(dedup.values(), key=lambda x: x["score"], reverse=True)[
            : settings.retrieval_top_k
        ]

        reranked = reranker.rerank(case.question, candidates)[: settings.rerank_top_k]
        top_context = reranked[: settings.context_top_k]
        gen = generator.pack_and_generate(db, case.question, top_context)

        retrieved_ids = [str(r["id"]) for r in candidates]
        cited_ids = [str(c.document_id) for c in gen.citations]
        context_text = " ".join(
            (r.get("payload") or {}).get("content", "") for r in top_context
        )

        rr = None
        if case.gold_chunk_ids:
            rr = eval_svc.score_retrieval_recall_at_k(
                retrieved_ids, case.gold_chunk_ids, k=settings.rerank_top_k,
            )
        cp = None
        if case.gold_doc_ids:
            cp = eval_svc.score_citation_precision(cited_ids, case.gold_doc_ids)

        ar = eval_svc.score_answer_relevance(case.question, gen.answer)
        ff = eval_svc.score_faithfulness(gen.answer, context_text)
        judge_score, judge_expl = eval_svc.score_llm_judge(
            case.question, case.expected, gen.answer, context_text,
        )
        lexical = eval_svc.score_lexical(case.expected, gen.answer)

        cr = CaseResult(
            question=case.question,
            expected=case.expected,
            actual=gen.answer,
            score=lexical,
            retrieval_recall=rr,
            citation_precision=cp,
            answer_relevance=ar,
            faithfulness=ff,
            llm_judge_score=judge_score,
            llm_judge_explanation=judge_expl,
        )
        results.append(cr)
        case_outputs.append(
            EvalCaseResult(
                question=cr.question,
                expected=cr.expected,
                actual=cr.actual,
                score=cr.score,
                retrieval_recall=cr.retrieval_recall,
                citation_precision=cr.citation_precision,
                answer_relevance=cr.answer_relevance,
                faithfulness=cr.faithfulness,
                llm_judge_score=cr.llm_judge_score,
                llm_judge_explanation=cr.llm_judge_explanation,
            )
        )

    run = eval_svc.record_run(
        db, current.tenant_id, payload.name, config={}, results=results,
    )
    return EvalRunResponse(
        run_id=run.id, name=run.name or "", metrics=run.metrics or {}, cases=case_outputs,
    )


@router.get("/runs", response_model=list[EvalRunSummary])
def list_runs(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvalRunSummary]:
    runs = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.tenant_id == current.tenant_id)
        .order_by(EvaluationRun.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        EvalRunSummary(
            run_id=r.id, name=r.name, metrics=r.metrics, created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=EvalRunSummary)
def get_run(
    run_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvalRunSummary:
    run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.id == run_id, EvaluationRun.tenant_id == current.tenant_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return EvalRunSummary(
        run_id=run.id, name=run.name, metrics=run.metrics, created_at=run.created_at,
    )
