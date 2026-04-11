import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.models.conversation import Conversation, Message
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationOut]:
    rows = (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == current.tenant_id,
            Conversation.user_id == current.id,
        )
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return [ConversationOut.model_validate(r) for r in rows]


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(
    conv_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conv_id,
            Conversation.tenant_id == current.tenant_id,
            Conversation.user_id == current.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.patch("/{conv_id}", response_model=ConversationOut)
def update_conversation(
    conv_id: uuid.UUID,
    payload: ConversationUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationOut:
    # Ownership is enforced inline: tenant + user must match before any write.
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conv_id,
            Conversation.tenant_id == current.tenant_id,
            Conversation.user_id == current.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
        )
    conv.title = payload.title
    db.commit()
    db.refresh(conv)
    return ConversationOut.model_validate(conv)


@router.post("/messages/{message_id}/feedback")
def set_feedback(
    message_id: uuid.UUID,
    payload: dict,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Set feedback on a message: {"value": 1} for thumbs up, {"value": -1} for thumbs down."""
    msg = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Message.id == message_id,
            Conversation.tenant_id == current.tenant_id,
        )
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message not found")
    value = payload.get("value", 0)
    if value not in (1, -1, 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="value must be 1, -1, or 0")
    msg.feedback = value if value != 0 else None
    db.commit()
    return {"message_id": str(message_id), "feedback": msg.feedback}


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conv_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    # Same ownership check; messages are removed automatically by the
    # ondelete="CASCADE" on messages.conversation_id (alembic 001_initial).
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conv_id,
            Conversation.tenant_id == current.tenant_id,
            Conversation.user_id == current.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
        )
    db.delete(conv)
    db.commit()
