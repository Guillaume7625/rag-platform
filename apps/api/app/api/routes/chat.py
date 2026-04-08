import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.db.models.conversation import Conversation, Message
from app.db.models.retrieval_trace import RetrievalTrace
from app.db.session import get_db
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.generation_service import get_generation
from app.services.query_router_service import decide_mode, decompose
from app.services.rerank_service import get_reranker
from app.services.retrieval_service import get_retrieval

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
    retrieved_all: list[dict] = []
    for q in queries:
        for c in retrieval.retrieve(
            query=q,
            tenant_id=current.tenant_id,
            allowed_roles=current.allowed_roles,
            tag_filters=payload.filters.get("tags") if payload.filters else None,
        ):
            retrieved_all.append({"id": c.id, "score": c.score, "payload": c.payload})

    # Dedup by id, keep max score.
    dedup: dict[str, dict] = {}
    for r in retrieved_all:
        cur = dedup.get(r["id"])
        if cur is None or r["score"] > cur["score"]:
            dedup[r["id"]] = r
    candidates = sorted(dedup.values(), key=lambda x: x["score"], reverse=True)[
        : settings.retrieval_top_k
    ]

    reranked = reranker.rerank(payload.query, candidates)[: settings.rerank_top_k]
    top_context = reranked[: settings.context_top_k]

    large = mode == "deep" or bool(
        top_context and top_context[0].get("rerank_score", 0.0) < 0.25
    )
    gen = generator.pack_and_generate(db, payload.query, top_context, large=large)

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
