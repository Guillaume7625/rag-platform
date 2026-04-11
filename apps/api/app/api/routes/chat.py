"""Chat endpoints: query (JSON) and stream (SSE).

Both use the shared retrieval pipeline for search + rerank,
then delegate to GenerationService for context selection + LLM call.
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.models.chunk import DocumentChunkParent
from app.db.models.conversation import Conversation, Message
from app.db.models.retrieval_trace import RetrievalTrace
from app.db.session import get_db
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.generation_service import (
    CLARIFICATION_PROMPT,
    SYSTEM_PROMPT,
    get_generation,
)
from app.services.llm_provider import get_llm
from app.services.query_router_service import decide_mode
from app.services.retrieval_pipeline import run_retrieval_pipeline

log = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_conversation(
    db: Session, payload: ChatQueryRequest, current: CurrentUser,
) -> Conversation:
    """Load existing conversation or create a new one."""
    conv = None
    if payload.conversation_id:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == payload.conversation_id,
                Conversation.tenant_id == current.tenant_id,
            )
            .first()
        )
    if conv is None:
        conv = Conversation(
            tenant_id=current.tenant_id,
            user_id=current.id,
            title=payload.query[:80],
        )
        db.add(conv)
        db.flush()
    return conv


def _build_context(
    db: Session,
    reranked: list[dict],
    generator: object,
) -> tuple[list[str], list[dict]]:
    """Build context blocks and citations from reranked chunks."""
    selected = generator._select_context(reranked, db)

    parent_ids = [
        uuid.UUID(r["payload"]["parent_id"])
        for r in selected
        if r["payload"].get("parent_id")
    ]
    parents: dict[uuid.UUID, DocumentChunkParent] = {}
    if parent_ids:
        for p in db.query(DocumentChunkParent).filter(
            DocumentChunkParent.id.in_(parent_ids),
        ).all():
            parents[p.id] = p

    context_blocks: list[str] = []
    citations: list[dict] = []

    for i, r in enumerate(selected, start=1):
        pay = r["payload"]
        pid = pay.get("parent_id")
        parent = parents.get(uuid.UUID(pid)) if pid else None
        text = parent.content if parent else pay.get("content", "")
        doc_name = pay.get("source_name") or "unknown"

        context_blocks.append(
            f"[{i}] (source: {doc_name}, page: {pay.get('page')})\n{text}",
        )
        if pay.get("document_id"):
            citations.append({
                "document_id": pay["document_id"],
                "document_name": doc_name,
                "page": pay.get("page"),
                "chunk_id": pay.get("chunk_id") or r["id"],
                "excerpt": (pay.get("content") or "")[:280],
            })

    return context_blocks, citations


def _save_trace(
    db: Session,
    message_id: uuid.UUID,
    query: str,
    mode: str,
    pipeline_result: object,
    generate_ms: int,
    confidence: float,
) -> None:
    """Persist retrieval trace for analytics."""
    db.add(RetrievalTrace(
        message_id=message_id,
        query=query,
        mode=mode,
        retrieved=[
            {"id": r["id"], "score": r["score"]}
            for r in pipeline_result.candidates[:20]
        ],
        reranked=[
            {"id": r["id"], "rerank_score": r.get("rerank_score")}
            for r in pipeline_result.reranked[:20]
        ],
        embed_ms=pipeline_result.timings.embed_ms,
        search_ms=pipeline_result.timings.search_ms,
        rerank_ms=pipeline_result.timings.rerank_ms,
        generate_ms=generate_ms,
        rerank_cache_hit=pipeline_result.timings.rerank_cache_hit,
        confidence=confidence,
        expansion_queries=pipeline_result.expanded_queries or None,
    ))


# ---------------------------------------------------------------------------
# POST /chat/query — JSON response
# ---------------------------------------------------------------------------

@router.post("/query", response_model=ChatQueryResponse)
def chat_query(
    payload: ChatQueryRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    t0 = time.time()
    mode = decide_mode(payload.query, payload.force_mode)

    # Retrieval pipeline (shared).
    result = run_retrieval_pipeline(
        query=payload.query,
        tenant_id=current.tenant_id,
        allowed_roles=current.allowed_roles,
        mode=mode,
        tag_filters=payload.filters.get("tags") if payload.filters else None,
    )

    # Generation.
    generator = get_generation()
    large = mode == "deep" or bool(
        result.reranked and result.reranked[0].get("rerank_score", 0.0) < 0.25,
    )
    t_gen = time.time()
    gen = generator.pack_and_generate(db, payload.query, result.reranked, large=large)
    generate_ms = int((time.time() - t_gen) * 1000)

    # Persist.
    conv = _get_or_create_conversation(db, payload, current)
    db.add(Message(conversation_id=conv.id, role="user", content=payload.query))

    latency_ms = int((time.time() - t0) * 1000)
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=gen.answer,
        citations=[c.model_dump(mode="json") for c in gen.citations],
        confidence=gen.confidence,
        mode_used=mode,
        latency_ms=latency_ms,
    )
    db.add(assistant_msg)
    db.flush()

    _save_trace(db, assistant_msg.id, payload.query, mode, result, generate_ms, gen.confidence)
    db.commit()

    return ChatQueryResponse(
        answer=gen.answer,
        citations=gen.citations,
        confidence=gen.confidence,
        mode_used=mode,
        latency_ms=latency_ms,
        conversation_id=conv.id,
        message_id=assistant_msg.id,
    )


# ---------------------------------------------------------------------------
# POST /chat/stream — Server-Sent Events
# ---------------------------------------------------------------------------

@router.post("/stream")
def chat_stream(
    payload: ChatQueryRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    t0 = time.time()
    mode = decide_mode(payload.query, payload.force_mode)
    generator = get_generation()
    llm = get_llm()

    # Retrieval pipeline (shared).
    result = run_retrieval_pipeline(
        query=payload.query,
        tenant_id=current.tenant_id,
        allowed_roles=current.allowed_roles,
        mode=mode,
        tag_filters=payload.filters.get("tags") if payload.filters else None,
    )

    # Build context.
    context_blocks, citations = _build_context(db, result.reranked, generator)
    confidence = generator._compute_confidence(result.reranked)
    system = CLARIFICATION_PROMPT if confidence < 0.70 else SYSTEM_PROMPT
    user_prompt = f"Question:\n{payload.query}\n\nContext:\n" + "\n\n".join(context_blocks)

    # Persist conversation + user message.
    conv = _get_or_create_conversation(db, payload, current)
    db.add(Message(conversation_id=conv.id, role="user", content=payload.query))
    db.flush()

    large = mode == "deep" or bool(
        result.reranked and result.reranked[0].get("rerank_score", 0.0) < 0.25,
    )

    def event_stream():
        meta = {
            "type": "meta",
            "conversation_id": str(conv.id),
            "confidence": round(confidence, 2),
            "mode": mode,
            "citations": citations,
        }
        yield f"data: {json.dumps(meta)}\n\n"

        full_answer: list[str] = []
        try:
            for chunk in llm.stream_anthropic(system, user_prompt, large=large):
                full_answer.append(chunk)
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
        except Exception as e:
            log.error("stream.generation_failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

        answer = "".join(full_answer)
        latency_ms = int((time.time() - t0) * 1000)
        msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            citations=citations,
            confidence=confidence,
            mode_used=mode,
            latency_ms=latency_ms,
        )
        db.add(msg)
        db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': str(msg.id), 'latency_ms': latency_ms})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
