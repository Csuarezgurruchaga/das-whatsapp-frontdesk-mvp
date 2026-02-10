from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.attachment_storage import store_attachment_binary
from app.db import crud
from app.db.base import Base
from app.db.models import (
    AttachmentMetadata,
    AttachmentStatus,
    Contact,
    Conversation,
    ConversationDeletionEvent,
    ConversationEvent,
    ConversationEventType,
    ConversationReadState,
    ConversationState,
    Message,
    MessageDirection,
    MessageReceipt,
    MessageReceiptStatus,
    SenderType,
    User,
    UserRole,
)
from app.hard_delete import hard_delete_conversation


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


def _next_id(session: Session, model: type) -> int:
    with session.no_autoflush:
        value = session.scalar(select(func.coalesce(func.max(model.id), 0)))
    return int(value or 0) + 1


def _write_export(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        archive.writestr("transcript.json", "{}")


class TestHardDeleteConversation(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _build_test_session()

        self.admin = User(
            id=1,
            username="admin1",
            password_hash="hash",
            role=UserRole.ADMIN,
        )
        self.agent = User(
            id=2,
            username="agent1",
            password_hash="hash",
            role=UserRole.AGENT,
        )
        self.contact = Contact(id=3, whatsapp_number="15550000003")
        self.conversation = Conversation(
            id=4,
            contact_id=self.contact.id,
            state=ConversationState.ASIGNADO,
            assigned_to=self.agent.id,
        )
        self.followup_conversation = Conversation(
            id=5,
            contact_id=self.contact.id,
            state=ConversationState.CERRADO,
            assigned_to=None,
            previous_conversation_id=self.conversation.id,
        )
        self.session.add_all(
            [
                self.admin,
                self.agent,
                self.contact,
                self.conversation,
                self.followup_conversation,
            ]
        )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()

    def _seed_conversation_artifacts(self, *, attachments_dir: str, exports_dir: str) -> None:
        message = crud.append_message(
            self.session,
            conversation_id=self.conversation.id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.AGENT,
            text="[attachment] evidence.pdf",
        )
        if message.id is None:
            message.id = _next_id(self.session, Message)

        relpath = store_attachment_binary(
            attachments_dir=attachments_dir,
            conversation_id=self.conversation.id,
            attachment_id="att-001",
            original_filename="evidence.pdf",
            content=b"evidence-bytes",
        )
        attachment = crud.create_attachment_metadata(
            self.session,
            conversation_id=self.conversation.id,
            message_id=message.id,
            attachment_id="att-001",
            original_filename="evidence.pdf",
            mime="application/pdf",
            size_bytes=len(b"evidence-bytes"),
            storage_relpath=relpath,
            status=AttachmentStatus.SENT,
            created_by=self.admin.id,
        )
        if attachment.id is None:
            attachment.id = _next_id(self.session, AttachmentMetadata)

        receipt = crud.create_message_receipt(
            self.session,
            status=MessageReceiptStatus.SENT,
            message_id=message.id,
            payload_raw="{}",
        )
        if receipt.id is None:
            receipt.id = _next_id(self.session, MessageReceipt)

        event = crud.create_conversation_event(
            self.session,
            conversation_id=self.conversation.id,
            event_type=ConversationEventType.CLOSED,
            actor_user_id=self.admin.id,
        )
        if event.id is None:
            event.id = _next_id(self.session, ConversationEvent)

        read_state = crud.upsert_read_state(
            self.session,
            conversation_id=self.conversation.id,
            user_id=self.agent.id,
            last_read_message_id=message.id,
        )
        if read_state.id is None:
            read_state.id = _next_id(self.session, ConversationReadState)

        _write_export(
            Path(exports_dir)
            / str(self.conversation.id)
            / f"conversation-{self.conversation.id}-exp001.zip"
        )
        nested_note = Path(exports_dir) / str(self.conversation.id) / "nested" / "note.txt"
        nested_note.parent.mkdir(parents=True, exist_ok=True)
        nested_note.write_text("temporary", encoding="utf-8")

        self.session.flush()

    def test_hard_delete_removes_conversation_artifacts_and_records_event(self) -> None:
        with TemporaryDirectory() as attachments_dir, TemporaryDirectory() as exports_dir:
            self._seed_conversation_artifacts(
                attachments_dir=attachments_dir,
                exports_dir=exports_dir,
            )
            attachment_file = (
                Path(attachments_dir)
                / str(self.conversation.id)
                / "att-001_evidence.pdf"
            )
            export_dir = Path(exports_dir) / str(self.conversation.id)
            self.assertTrue(attachment_file.exists())
            self.assertTrue(export_dir.exists())

            result = hard_delete_conversation(
                self.session,
                conversation_id=self.conversation.id,
                actor_user_id=self.admin.id,
                reason="  legal request  ",
                now=datetime(2026, 2, 6, 21, 0, tzinfo=timezone.utc),
                attachments_dir=attachments_dir,
                exports_dir=exports_dir,
            )
            self.session.commit()

            self.assertEqual(result.deleted_conversation_rows, 1)
            self.assertEqual(result.deleted_attachment_files, 1)
            self.assertEqual(result.missing_attachment_files, 0)
            self.assertEqual(result.deleted_export_files, 2)
            self.assertEqual(result.deleted_attachment_rows, 1)
            self.assertEqual(result.deleted_message_rows, 1)
            self.assertEqual(result.deleted_message_receipt_rows, 1)
            self.assertEqual(result.deleted_read_state_rows, 1)
            self.assertEqual(result.deleted_conversation_event_rows, 1)
            self.assertEqual(result.cleared_previous_conversation_references, 1)

            self.assertIsNone(
                crud.get_conversation(self.session, conversation_id=self.conversation.id)
            )
            followup = crud.get_conversation(
                self.session, conversation_id=self.followup_conversation.id
            )
            self.assertIsNotNone(followup)
            self.assertIsNone(followup.previous_conversation_id)
            self.assertFalse(attachment_file.exists())
            self.assertFalse(export_dir.exists())

            deletion_events = crud.list_conversation_deletion_events(
                self.session, conversation_id=self.conversation.id
            )
            self.assertEqual(len(deletion_events), 1)
            self.assertEqual(deletion_events[0].actor_user_id, self.admin.id)
            self.assertEqual(deletion_events[0].reason, "legal request")

            total_conversation_events = self.session.scalar(
                select(func.count(ConversationEvent.id))
            )
            self.assertEqual(int(total_conversation_events or 0), 0)
            total_messages = self.session.scalar(select(func.count(Message.id)))
            self.assertEqual(int(total_messages or 0), 0)
            total_attachments = self.session.scalar(select(func.count(AttachmentMetadata.id)))
            self.assertEqual(int(total_attachments or 0), 0)
            total_receipts = self.session.scalar(select(func.count(MessageReceipt.id)))
            self.assertEqual(int(total_receipts or 0), 0)
            total_read_states = self.session.scalar(select(func.count(ConversationReadState.id)))
            self.assertEqual(int(total_read_states or 0), 0)
            total_deletion_events = self.session.scalar(
                select(func.count(ConversationDeletionEvent.id))
            )
            self.assertEqual(int(total_deletion_events or 0), 1)

    def test_hard_delete_rejects_non_admin_actor(self) -> None:
        with TemporaryDirectory() as attachments_dir, TemporaryDirectory() as exports_dir:
            self._seed_conversation_artifacts(
                attachments_dir=attachments_dir,
                exports_dir=exports_dir,
            )
            with self.assertRaisesRegex(PermissionError, "admin role required"):
                hard_delete_conversation(
                    self.session,
                    conversation_id=self.conversation.id,
                    actor_user_id=self.agent.id,
                    attachments_dir=attachments_dir,
                    exports_dir=exports_dir,
                )

            self.assertIsNotNone(
                crud.get_conversation(self.session, conversation_id=self.conversation.id)
            )
            deletion_events = crud.list_conversation_deletion_events(
                self.session, conversation_id=self.conversation.id
            )
            self.assertEqual(deletion_events, [])

    def test_hard_delete_rejects_unknown_conversation(self) -> None:
        with TemporaryDirectory() as attachments_dir, TemporaryDirectory() as exports_dir:
            with self.assertRaisesRegex(ValueError, "conversation not found"):
                hard_delete_conversation(
                    self.session,
                    conversation_id=99999,
                    actor_user_id=self.admin.id,
                    attachments_dir=attachments_dir,
                    exports_dir=exports_dir,
                )


if __name__ == "__main__":
    unittest.main()
