from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db import crud
from app.db.models import (
    AttachmentStatus,
    ConversationEventType,
    ConversationState,
    MessageDirection,
    MessageReceiptStatus,
    SenderType,
    User,
    UserRole,
)


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


class TestSqliteBigIntFallbacks(unittest.TestCase):
    def setUp(self) -> None:
        self.db = _build_test_session()
        self.user = User(id=1, username="admin1", password_hash="hash", role=UserRole.ADMIN)
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_create_user_session_assigns_sqlite_id(self) -> None:
        session = crud.create_user_session(
            self.db,
            session_id="sess1",
            user_id=self.user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.db.commit()
        self.assertEqual(session.id, 1)

    def test_create_login_event_assigns_sqlite_id(self) -> None:
        event = crud.create_conversation_event(
            self.db,
            conversation_id=None,
            event_type=ConversationEventType.LOGIN_SUCCESS,
            actor_user_id=self.user.id,
        )
        self.db.commit()
        self.assertEqual(event.id, 1)

    def test_core_entities_assign_sqlite_ids(self) -> None:
        contact = crud.create_contact(
            self.db,
            whatsapp_number="5491112345678",
            display_name="Carlos",
        )
        self.db.flush()
        self.assertEqual(contact.id, 1)

        conversation = crud.create_conversation(
            self.db,
            contact_id=contact.id,
            state=ConversationState.CHATBOT,
        )
        self.db.flush()
        self.assertEqual(conversation.id, 1)

        message = crud.append_message(
            self.db,
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            sender_type=SenderType.USER,
            text="hola",
            whatsapp_message_id="wamid.1",
        )
        self.db.flush()
        self.assertEqual(message.id, 1)

    def test_multiple_messages_before_flush_get_distinct_sqlite_ids(self) -> None:
        contact = crud.create_contact(
            self.db,
            whatsapp_number="5491112345681",
            display_name="Marta",
        )
        self.db.flush()

        conversation = crud.create_conversation(
            self.db,
            contact_id=contact.id,
            state=ConversationState.CHATBOT,
        )
        self.db.flush()

        first = crud.append_message(
            self.db,
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            sender_type=SenderType.USER,
            text="uno",
            whatsapp_message_id="wamid.multi.1",
        )
        second = crud.append_message(
            self.db,
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.BOT,
            text="dos",
            whatsapp_message_id="wamid.multi.2",
        )
        self.db.flush()
        self.assertEqual(first.id, 1)
        self.assertEqual(second.id, 2)

    def test_receipts_and_attachments_assign_sqlite_ids(self) -> None:
        contact = crud.create_contact(
            self.db,
            whatsapp_number="5491112345679",
            display_name="Ana",
        )
        self.db.flush()

        conversation = crud.create_conversation(
            self.db,
            contact_id=contact.id,
            state=ConversationState.ASIGNADO,
            assigned_to=self.user.id,
        )
        self.db.flush()

        message = crud.append_message(
            self.db,
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.AGENT,
            text="ok",
            whatsapp_message_id="wamid.2",
        )
        self.db.flush()

        receipt = crud.create_message_receipt(
            self.db,
            message_id=message.id,
            status=MessageReceiptStatus.SENT,
        )
        self.db.flush()
        self.assertEqual(receipt.id, 1)

        attachment = crud.create_attachment_metadata(
            self.db,
            conversation_id=conversation.id,
            message_id=message.id,
            attachment_id="att-1",
            original_filename="test.txt",
            mime="text/plain",
            size_bytes=10,
            storage_relpath="attachments/test.txt",
            status=AttachmentStatus.SENT,
            created_by=self.user.id,
        )
        self.db.flush()
        self.assertEqual(attachment.id, 1)

    def test_read_state_assigns_sqlite_id(self) -> None:
        contact = crud.create_contact(
            self.db,
            whatsapp_number="5491112345680",
            display_name="Leo",
        )
        self.db.flush()

        conversation = crud.create_conversation(
            self.db,
            contact_id=contact.id,
            state=ConversationState.CHATBOT,
        )
        self.db.flush()

        message = crud.append_message(
            self.db,
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            sender_type=SenderType.USER,
            text="hola",
            whatsapp_message_id="wamid.3",
        )
        self.db.flush()

        read_state = crud.upsert_read_state(
            self.db,
            conversation_id=conversation.id,
            user_id=self.user.id,
            last_read_message_id=message.id,
        )
        self.db.flush()
        self.assertEqual(read_state.id, 1)
