import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.db.models.conversation import Conversation, Message
from app.db.models.retrieval_trace import RetrievalTrace
from app.db.session import get_db
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.generation_service import GenerationResult, get_generation
from app.services.query_expansion_service import get_query_expansion
from app.services.query_router_service import decide_mode, decompose
from app.services.rerank_service import get_reranker
from app.services.retrieval_service import get_retrieval

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

CONFIDENCE_THRESHOLD = 0.70
MAX_ATTEMPTS = 2


def _run_rag_pipeline(
    query: str,
    mode: str,
    current: CurrentUser,
    db: Session,
    payload: ChatQueryRequest,
    *,
    expansion_count: int = 2,
    retrieval_top_k: int | None = None,
    force_large: bool = False,
) -> tuple[GenerationResult, list[dict], list[dict], list[str], dict[str, float]]:
    """Run the full RAG pipeline and return (result, candidates, reranked, expanded, timings)."""
    retrieval = get_retrieval()
    reranker = get_reranker()
    generator = get_generation()
    expander = get_query_expansion()

    queries = decompose(query) if mode == "deep" else [query]
    expanded = expander.expand(query, n=expansion_count)
    queries = queries + expanded

    top_k = retrieval_top_k or settings.retrieval_top_k

    t_embed = time.time()
    retrieved_all: list[dict] = []
    for q in queries:
        for c in retrieval.retrieve(
            query=q,
            tenant_id=current.tenant_id,
            allowed_roles=current.allowed_roles,
            tag_filters=payload.filters.get("tags") if payload.filters else None,
            top_k=top_k,
        ):
            retrieved_all.append({"id": c.id, "score": c.score, "payload": c.payload})
    t_search = time.time()

    # Dedup by id, keep max score.
    dedup: dict[str, dict] = {}
    for r in retrieved_all:
        cur = dedup.get(r["id"])
        if cur is None or r["score"] > cur["score"]:
            dedup[r["id"]] = r
    candidates = sorted(dedup.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    t_rerank = time.time()
    reranked = reranker.rerank(query, candidates)[: settings.rerank_top_k]
    t_rerank_end = time.time()

    large = force_large or mode == "deep" or bool(
        reranked and reranked[0].get("rerank_score", 0.0) < 0.25
    )
    t_gen = time.time()
    gen = generator.pack_and_generate(db, query, reranked, large=large)
    t_gen_end = time.time()

    timings = {
        "embed_ms": (t_search - t_embed) * 1000,
        "search_ms": (t_rerank - t_search) * 1000,
        "rerank_ms": (t_rerank_end - t_rerank) * 1000,
        "generate_ms": (t_gen_end - t_gen) * 1000,
    }

    return gen, candidates, reranked, expanded, timings


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(
    payload: ChatQueryRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    t0 = time.time()

    mode = decide_mode(payload.query, payload.force_mode)
    reranker = get_reranker()

    # --- Pass 1: standard ---
    gen, candidates, reranked, expanded, timings = _run_rag_pipeline(
        query=payload.query,
        mode=mode,
        current=current,
        db=db,
        payload=payload,
        expansion_count=settings.query_expansion_count,
    )

    attempt = 1

    # --- Pass 2: retry if confidence too low ---
    if gen.confidence < CONFIDENCE_THRESHOLD and attempt < MAX_ATTEMPTS:
        log.info(
            "rag.retry confidence=%.2f < %.2f, retrying with expanded search",
            gen.confidence, CONFIDENCE_THRESHOLD,
        )
        gen2, candidates2, reranked2, expanded2, timings2 = _run_rag_pipeline(
            query=payload.query,
            mode=mode,
            current=current,
            db=db,
            payload=payload,
            expansion_count=5,  # more reformulations
            retrieval_top_k=settings.retrieval_top_k * 2,  # wider search
            force_large=True,  # use Sonnet
        )
        attempt += 1

        # Keep the better result
        if gen2.confidence > gen.confidence:
            log.info(
                "rag.retry_improved %.2f -> %.2f",
                gen.confidence, gen2.confidence,
            )
            gen, candidates, reranked, expanded, timings = (
                gen2, candidates2, reranked2, expanded2, timings2,
            )

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
    mode_label = f"{mode}" if attempt == 1 else f"{mode}+retry"
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=gen.answer,
        citations=[c.model_dump(mode="json") for c in gen.citations],
        confidence=gen.confidence,
        mode_used=mode_label,
        latency_ms=latency_ms,
    )
    db.add(assistant_msg)
    db.flush()

    db.add(
        RetrievalTrace(
            message_id=assistant_msg.id,
            query=payload.query,
            mode=mode_label,
            retrieved=[{"id": r["id"], "score": r["score"]} for r in candidates[:20]],
            reranked=[
                {"id": r["id"], "rerank_score": r.get("rerank_score")} for r in reranked[:20]
            ],
            embed_ms=int(timings["embed_ms"]),
            search_ms=int(timings["search_ms"]),
            rerank_ms=int(timings["rerank_ms"]),
            generate_ms=int(timings["generate_ms"]),
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
        mode_used=mode_label,
        latency_ms=latency_ms,
        conversation_id=conv.id,
        message_id=assistant_msg.id,
    )
