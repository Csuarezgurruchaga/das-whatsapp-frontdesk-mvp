from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .models import (
    Contact,
    Conversation,
    ConversationReadState,
    ConversationState,
    ConversationEvent,
    ConversationEventType,
    Message,
    MessageDirection,
    MessageReceipt,
    MessageReceiptStatus,
    SenderType,
    User,
    UserSession,
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


def update_conversation_state(
    session: Session,
    *,
    conversation_id: int,
    state: ConversationState,
    assigned_to: int | None,
    now: datetime,
) -> None:
    stmt = (
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            state=state,
            assigned_to=assigned_to,
            last_activity_at=now,
            updated_at=now,
        )
    )
    session.execute(stmt)


def touch_conversation(session: Session, *, conversation_id: int, now: datetime) -> None:
    stmt = (
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            last_activity_at=now,
            updated_at=now,
        )
    )
    session.execute(stmt)


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


def list_conversations_by_state_and_assignee(
    session: Session,
    *,
    state: ConversationState,
    assignee_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(
            Conversation.state == state,
            Conversation.assigned_to == assignee_id,
        )
        .order_by(Conversation.last_activity_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def get_latest_conversation_for_contact(
    session: Session,
    *,
    contact_id: int,
) -> Conversation | None:
    stmt = (
        select(Conversation)
        .where(Conversation.contact_id == contact_id)
        .order_by(Conversation.last_activity_at.desc())
        .limit(1)
    )
    return session.scalar(stmt)


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


def get_contact_by_whatsapp_number(
    session: Session,
    *,
    whatsapp_number: str,
) -> Contact | None:
    stmt = select(Contact).where(Contact.whatsapp_number == whatsapp_number)
    return session.scalar(stmt)


def create_contact(
    session: Session,
    *,
    whatsapp_number: str,
    display_name: str | None = None,
) -> Contact:
    contact = Contact(
        whatsapp_number=whatsapp_number,
        display_name=display_name,
    )
    session.add(contact)
    return contact


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


def get_message_by_whatsapp_message_id(
    session: Session,
    *,
    whatsapp_message_id: str,
) -> Message | None:
    stmt = (
        select(Message)
        .where(Message.whatsapp_message_id == whatsapp_message_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def list_messages(
    session: Session,
    *,
    conversation_id: int,
    limit: int = 200,
    offset: int = 0,
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def get_last_message(
    session: Session,
    *,
    conversation_id: int,
) -> Message | None:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def list_bot_message_texts(
    session: Session,
    *,
    conversation_id: int,
) -> list[str]:
    session.flush()
    stmt = (
        select(Message.text)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_type == SenderType.BOT,
        )
        .order_by(Message.created_at.asc())
    )
    return [text for text in session.scalars(stmt) if text]


def get_last_bot_message_text(
    session: Session,
    *,
    conversation_id: int,
) -> str | None:
    session.flush()
    stmt = (
        select(Message.text)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_type == SenderType.BOT,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def create_conversation_event(
    session: Session,
    *,
    conversation_id: int | None,
    event_type: ConversationEventType,
    actor_user_id: int | None = None,
    meta_json: str | None = None,
) -> ConversationEvent:
    if conversation_id is None and event_type not in {
        ConversationEventType.LOGIN_SUCCESS,
        ConversationEventType.LOGIN_FAIL,
    }:
        raise ValueError("conversation_id is required for non-login events")

    event = ConversationEvent(
        conversation_id=conversation_id,
        type=event_type,
        actor_user_id=actor_user_id,
        meta_json=meta_json,
    )
    session.add(event)
    return event


def list_conversation_events(
    session: Session,
    *,
    conversation_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[ConversationEvent]:
    stmt = (
        select(ConversationEvent)
        .where(ConversationEvent.conversation_id == conversation_id)
        .order_by(ConversationEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def create_message_receipt(
    session: Session,
    *,
    status: MessageReceiptStatus,
    message_id: int | None = None,
    whatsapp_message_id: str | None = None,
    payload_raw: str | None = None,
) -> MessageReceipt:
    if message_id is None and whatsapp_message_id is None:
        raise ValueError("message_id or whatsapp_message_id is required")

    receipt = MessageReceipt(
        message_id=message_id,
        whatsapp_message_id=whatsapp_message_id,
        status=status,
        payload_raw=payload_raw,
    )
    session.add(receipt)
    return receipt


def list_message_receipts_by_conversation(
    session: Session,
    *,
    conversation_id: int,
    limit: int = 200,
    offset: int = 0,
) -> list[MessageReceipt]:
    stmt = (
        select(MessageReceipt)
        .join(Message, MessageReceipt.message_id == Message.id)
        .where(Message.conversation_id == conversation_id)
        .order_by(MessageReceipt.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def list_message_receipts_by_whatsapp_message_id(
    session: Session,
    *,
    whatsapp_message_id: str,
    limit: int = 200,
    offset: int = 0,
) -> list[MessageReceipt]:
    stmt = (
        select(MessageReceipt)
        .where(MessageReceipt.whatsapp_message_id == whatsapp_message_id)
        .order_by(MessageReceipt.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def get_user_by_username(session: Session, *, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return session.scalar(stmt)


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def create_user_session(
    session: Session,
    *,
    session_id: str,
    user_id: int,
    expires_at: datetime,
) -> UserSession:
    user_session = UserSession(
        session_id=session_id,
        user_id=user_id,
        expires_at=expires_at,
    )
    session.add(user_session)
    return user_session


def get_user_session_by_session_id(
    session: Session,
    *,
    session_id: str,
) -> UserSession | None:
    stmt = select(UserSession).where(UserSession.session_id == session_id)
    return session.scalar(stmt)


def revoke_user_session(
    session: Session,
    user_session: UserSession,
    *,
    revoked_at: datetime | None = None,
) -> UserSession:
    user_session.revoked_at = revoked_at or datetime.now(timezone.utc)
    return user_session


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


def get_read_state(
    session: Session,
    *,
    conversation_id: int,
    user_id: int,
) -> ConversationReadState | None:
    stmt = select(ConversationReadState).where(
        ConversationReadState.conversation_id == conversation_id,
        ConversationReadState.user_id == user_id,
    )
    return session.scalar(stmt)


def count_unread_messages(
    session: Session,
    *,
    conversation_id: int,
    last_read_message_id: int | None,
) -> int:
    stmt = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id,
        Message.direction == MessageDirection.INBOUND,
    )
    if last_read_message_id is not None:
        stmt = stmt.where(Message.id > last_read_message_id)
    return int(session.scalar(stmt) or 0)


def list_users_by_role(
    session: Session,
    *,
    role: UserRole,
) -> list[User]:
    stmt = (
        select(User)
        .where(
            User.role == role,
            User.disabled_at.is_(None),
        )
        .order_by(User.username.asc())
    )
    return list(session.scalars(stmt))
