import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.db.models.conversation import Conversation, Message
from app.db.models.retrieval_trace import RetrievalTrace
from app.db.session import get_db
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.generation_service import get_generation
from app.services.query_expansion_service import get_query_expansion
from app.services.query_router_service import decide_mode, decompose
from app.services.rerank_service import get_reranker
from app.services.retrieval_service import get_retrieval

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(
    payload: ChatQueryRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    t0 = time.time()

    mode = decide_mode(payload.query, payload.force_mode)
    retrieval = get_retrieval()
    reranker = get_reranker()
    generator = get_generation()

    queries = decompose(payload.query) if mode == "deep" else [payload.query]
    expander = get_query_expansion()
    expanded = expander.expand(payload.query, n=settings.query_expansion_count)
    queries = queries + expanded

    t_embed = time.time()
    retrieved_all: list[dict] = []
    for q in queries:
        for c in retrieval.retrieve(
            query=q,
            tenant_id=current.tenant_id,
            allowed_roles=current.allowed_roles,
            tag_filters=payload.filters.get("tags") if payload.filters else None,
        ):
            retrieved_all.append({"id": c.id, "score": c.score, "payload": c.payload})
    t_search = time.time()

    # Dedup by id, keep max score.
    dedup: dict[str, dict] = {}
    for r in retrieved_all:
        cur = dedup.get(r["id"])
        if cur is None or r["score"] > cur["score"]:
            dedup[r["id"]] = r
    candidates = sorted(dedup.values(), key=lambda x: x["score"], reverse=True)[
        : settings.retrieval_top_k
    ]

    t_rerank = time.time()
    reranked = reranker.rerank(payload.query, candidates)[: settings.rerank_top_k]
    t_rerank_end = time.time()

    large = mode == "deep" or bool(
        reranked and reranked[0].get("rerank_score", 0.0) < 0.25
    )
    t_gen = time.time()
    # Pass all reranked chunks. Generation service handles diversity, budget,
    # and will switch to clarification prompt if confidence < 70%.
    gen = generator.pack_and_generate(db, payload.query, reranked, large=large)
    t_gen_end = time.time()

    # Persist conversation + message.
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

    db.add(
        RetrievalTrace(
            message_id=assistant_msg.id,
            query=payload.query,
            mode=mode,
            retrieved=[{"id": r["id"], "score": r["score"]} for r in candidates[:20]],
            reranked=[
                {"id": r["id"], "rerank_score": r.get("rerank_score")} for r in reranked[:20]
            ],
            embed_ms=int((t_search - t_embed) * 1000),
            search_ms=int((t_rerank - t_search) * 1000),
            rerank_ms=int((t_rerank_end - t_rerank) * 1000),
            generate_ms=int((t_gen_end - t_gen) * 1000),
            rerank_cache_hit=reranker.last_cache_hit,
            confidence=gen.confidence,
            expansion_queries=expanded if expanded else None,
        )
    )
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


@router.post("/stream")
def chat_stream(
    payload: ChatQueryRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """SSE endpoint: streams the answer token by token."""
    from app.services.generation_service import CLARIFICATION_PROMPT, SYSTEM_PROMPT
    from app.services.llm_provider import get_llm

    t0 = time.time()
    mode = decide_mode(payload.query, payload.force_mode)
    retrieval = get_retrieval()
    reranker = get_reranker()
    generator = get_generation()
    expander = get_query_expansion()
    llm = get_llm()

    queries = decompose(payload.query) if mode == "deep" else [payload.query]
    expanded = expander.expand(payload.query, n=settings.query_expansion_count)
    queries = queries + expanded

    retrieved_all: list[dict] = []
    for q in queries:
        for c in retrieval.retrieve(
            query=q, tenant_id=current.tenant_id,
            allowed_roles=current.allowed_roles,
            tag_filters=payload.filters.get("tags") if payload.filters else None,
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
    reranked = reranker.rerank(payload.query, candidates)[: settings.rerank_top_k]

    # Build context (reuse generation service logic).
    selected = generator._select_context(reranked, db)
    import uuid as _uuid

    from app.db.models.chunk import DocumentChunkParent

    parent_ids = [_uuid.UUID(r["payload"]["parent_id"]) for r in selected if r["payload"].get("parent_id")]
    parents: dict = {}
    if parent_ids:
        for p in db.query(DocumentChunkParent).filter(DocumentChunkParent.id.in_(parent_ids)).all():
            parents[p.id] = p

    context_blocks: list[str] = []
    citations: list[dict] = []
    for i, r in enumerate(selected, start=1):
        pay = r["payload"]
        pid = pay.get("parent_id")
        parent = parents.get(_uuid.UUID(pid)) if pid else None
        text = parent.content if parent else pay.get("content", "")
        doc_name = pay.get("source_name") or "unknown"
        context_blocks.append(f"[{i}] (source: {doc_name}, page: {pay.get('page')})\n{text}")
        if pay.get("document_id"):
            citations.append({
                "document_id": pay["document_id"], "document_name": doc_name,
                "page": pay.get("page"), "chunk_id": pay.get("chunk_id") or r["id"],
                "excerpt": (pay.get("content") or "")[:280],
            })

    confidence = generator._compute_confidence(reranked)
    system = CLARIFICATION_PROMPT if confidence < 0.70 else SYSTEM_PROMPT
    user_prompt = f"Question:\n{payload.query}\n\nContext:\n" + "\n\n".join(context_blocks)

    # Persist conversation.
    conv = None
    if payload.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == payload.conversation_id,
            Conversation.tenant_id == current.tenant_id,
        ).first()
    if conv is None:
        conv = Conversation(tenant_id=current.tenant_id, user_id=current.id, title=payload.query[:80])
        db.add(conv)
        db.flush()
    db.add(Message(conversation_id=conv.id, role="user", content=payload.query))
    db.flush()

    def event_stream():
        # Send metadata first.
        meta = {
            "type": "meta",
            "conversation_id": str(conv.id),
            "confidence": round(confidence, 2),
            "mode": mode,
            "citations": citations,
        }
        yield f"data: {json.dumps(meta)}\n\n"

        # Stream tokens.
        full_answer = []
        large = mode == "deep" or bool(reranked and reranked[0].get("rerank_score", 0.0) < 0.25)
        try:
            for chunk in llm.stream_anthropic(system, user_prompt, large=large):
                full_answer.append(chunk)
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

        # Save assistant message.
        answer = "".join(full_answer)
        latency_ms = int((time.time() - t0) * 1000)
        msg = Message(
            conversation_id=conv.id, role="assistant", content=answer,
            citations=[c for c in citations],
            confidence=confidence, mode_used=mode, latency_ms=latency_ms,
        )
        db.add(msg)
        db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': str(msg.id), 'latency_ms': latency_ms})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
