from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Conversation,
    ConversationReadState,
    ConversationState,
    Message,
    MessageDirection,
    SenderType,
)


def create_conversation(
    session: Session,
    *,
    contact_id: int,
    state: ConversationState,
    assigned_to: int | None = None,
    previous_conversation_id: int | None = None,
) -> Conversation:
    conversation = Conversation(
        contact_id=contact_id,
        state=state,
        assigned_to=assigned_to,
        previous_conversation_id=previous_conversation_id,
    )
    session.add(conversation)
    return conversation


def get_conversation(session: Session, conversation_id: int) -> Conversation | None:
    return session.get(Conversation, conversation_id)


def list_conversations_by_state(
    session: Session,
    *,
    state: ConversationState,
    limit: int = 100,
    offset: int = 0,
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.state == state)
        .order_by(Conversation.last_activity_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def update_conversation(
    session: Session,
    conversation: Conversation,
    *,
    state: ConversationState | None = None,
    assigned_to: int | None = None,
    closed_by: int | None = None,
    closed_at: datetime | None = None,
    last_activity_at: datetime | None = None,
) -> Conversation:
    if state is not None:
        conversation.state = state
    if assigned_to is not None or conversation.state != ConversationState.ASIGNADO:
        conversation.assigned_to = assigned_to
    if closed_by is not None:
        conversation.closed_by = closed_by
    if closed_at is not None:
        conversation.closed_at = closed_at
    if last_activity_at is not None:
        conversation.last_activity_at = last_activity_at
    return conversation


def append_message(
    session: Session,
    *,
    conversation_id: int,
    direction: MessageDirection,
    sender_type: SenderType,
    text: str | None = None,
    whatsapp_message_id: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        direction=direction,
        sender_type=sender_type,
        text=text,
        whatsapp_message_id=whatsapp_message_id,
    )
    session.add(message)
    return message


def upsert_read_state(
    session: Session,
    *,
    conversation_id: int,
    user_id: int,
    last_read_message_id: int | None,
    last_read_at: datetime | None = None,
) -> ConversationReadState:
    stmt = select(ConversationReadState).where(
        ConversationReadState.conversation_id == conversation_id,
        ConversationReadState.user_id == user_id,
    )
    read_state = session.scalar(stmt)
    if read_state is None:
        read_state = ConversationReadState(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        session.add(read_state)

    read_state.last_read_message_id = last_read_message_id
    read_state.last_read_at = last_read_at or datetime.now(timezone.utc)
    return read_state
