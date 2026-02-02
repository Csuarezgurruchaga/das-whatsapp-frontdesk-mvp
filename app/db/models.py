import enum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserRole(enum.Enum):
    AGENT = "agent"
    ADMIN = "admin"


class ConversationState(enum.Enum):
    CHATBOT = "CHATBOT"
    EN_ESPERA = "EN_ESPERA"
    ASIGNADO = "ASIGNADO"
    CERRADO = "CERRADO"


class MessageDirection(enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class SenderType(enum.Enum):
    USER = "USER"
    BOT = "BOT"
    AGENT = "AGENT"


class ConversationEventType(enum.Enum):
    TAKEN = "TAKEN"
    REASSIGNED = "REASSIGNED"
    CLOSED = "CLOSED"
    MESSAGE_SENT_FAILED = "MESSAGE_SENT_FAILED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAIL = "LOGIN_FAIL"


class MessageReceiptStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    disabled_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    whatsapp_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "(state = 'ASIGNADO' AND assigned_to IS NOT NULL) OR "
            "(state <> 'ASIGNADO' AND assigned_to IS NULL)",
            name="ck_conversations_assigned_to_matches_state",
        ),
        Index("ix_conversations_state_last_activity", "state", "last_activity_at"),
        Index("ix_conversations_assigned_last_activity", "assigned_to", "last_activity_at"),
        Index("ix_conversations_contact_id", "contact_id"),
        Index("ix_conversations_previous_conversation_id", "previous_conversation_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    state: Mapped[ConversationState] = mapped_column(
        Enum(ConversationState, name="conversation_state"), nullable=False
    )
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_activity_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    previous_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id")
    )

    contact = relationship("Contact")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    closed_by_user = relationship("User", foreign_keys=[closed_by])
    previous_conversation = relationship("Conversation", remote_side=[id])


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created_at", "conversation_id", "created_at"),
        Index("ix_messages_whatsapp_message_id", "whatsapp_message_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="message_direction"), nullable=False
    )
    sender_type: Mapped[SenderType] = mapped_column(
        Enum(SenderType, name="message_sender_type"), nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("Conversation")


class ConversationEvent(Base):
    __tablename__ = "conversation_events"
    __table_args__ = (
        Index("ix_conversation_events_conversation_id", "conversation_id"),
        Index("ix_conversation_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    type: Mapped[ConversationEventType] = mapped_column(
        Enum(ConversationEventType, name="conversation_event_type"), nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    meta_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("Conversation")
    actor_user = relationship("User")


class MessageReceipt(Base):
    __tablename__ = "message_receipts"
    __table_args__ = (
        CheckConstraint(
            "message_id IS NOT NULL OR whatsapp_message_id IS NOT NULL",
            name="ck_message_receipts_message_or_whatsapp_id",
        ),
        Index("ix_message_receipts_message_id", "message_id"),
        Index("ix_message_receipts_whatsapp_message_id", "whatsapp_message_id"),
        Index("ix_message_receipts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[MessageReceiptStatus] = mapped_column(
        Enum(MessageReceiptStatus, name="message_receipt_status"), nullable=False
    )
    payload_raw: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    message = relationship("Message")


class ConversationReadState(Base):
    __tablename__ = "conversation_read_states"
    __table_args__ = (
        Index("ix_read_state_conversation_id", "conversation_id"),
        Index("ix_read_state_user_id", "user_id"),
        UniqueConstraint("conversation_id", "user_id", name="uq_read_state_conversation_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_read_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    last_read_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

    conversation = relationship("Conversation")
    user = relationship("User")
    last_read_message = relationship("Message")
