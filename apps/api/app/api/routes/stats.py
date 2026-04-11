"""Dashboard statistics endpoint."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.models.conversation import Conversation, Message
from app.db.models.document import Document
from app.db.session import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
def dashboard_stats(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    tenant = current.tenant_id

    # Documents
    total_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant
    ).scalar() or 0
    indexed_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant, Document.state == "indexed"
    ).scalar() or 0
    failed_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant, Document.state == "failed"
    ).scalar() or 0

    # Conversations & messages
    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant
    ).scalar() or 0

    total_messages = db.query(func.count(Message.id)).join(Conversation).filter(
        Conversation.tenant_id == tenant, Message.role == "user"
    ).scalar() or 0

    # Recent activity (last 7 days)
    week_ago = datetime.now(UTC) - timedelta(days=7)
    recent_messages = db.query(func.count(Message.id)).join(Conversation).filter(
        Conversation.tenant_id == tenant,
        Message.role == "user",
        Message.created_at >= week_ago,
    ).scalar() or 0

    recent_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant,
        Conversation.created_at >= week_ago,
    ).scalar() or 0

    # Average latency (from assistant messages)
    avg_latency = db.query(func.avg(Message.latency_ms)).join(Conversation).filter(
        Conversation.tenant_id == tenant,
        Message.role == "assistant",
        Message.latency_ms.isnot(None),
    ).scalar()

    # Average confidence
    avg_confidence = db.query(func.avg(Message.confidence)).join(Conversation).filter(
        Conversation.tenant_id == tenant,
        Message.role == "assistant",
        Message.confidence.isnot(None),
    ).scalar()

    # Recent conversations
    recent_convs = db.query(Conversation).filter(
        Conversation.tenant_id == tenant
    ).order_by(Conversation.created_at.desc()).limit(5).all()

    return {
        "documents": {
            "total": total_docs,
            "indexed": indexed_docs,
            "failed": failed_docs,
        },
        "conversations": {
            "total": total_conversations,
            "recent_7d": recent_conversations,
        },
        "messages": {
            "total": total_messages,
            "recent_7d": recent_messages,
        },
        "performance": {
            "avg_latency_ms": round(avg_latency) if avg_latency else None,
            "avg_confidence": round(avg_confidence, 2) if avg_confidence else None,
        },
        "recent_conversations": [
            {
                "id": str(c.id),
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent_convs
        ],
    }
