from __future__ import annotations

from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.attachment_pipeline import send_outbound_attachment
from app.config import ExtrasConfig, get_extras_config
from app.db import crud
from app.db.base import Base
from app.db.models import (
    AttachmentMetadata,
    AttachmentStatus,
    Contact,
    Conversation,
    ConversationEvent,
    ConversationState,
    Message,
    MessageReceipt,
    User,
    UserRole,
)
from app.whatsapp import WhatsAppSendError, WhatsAppSendResponse


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


def _next_id(session: Session, model: type) -> int:
    with session.no_autoflush:
        value = session.scalar(select(func.coalesce(func.max(model.id), 0)))
    return int(value or 0) + 1


class TestAttachmentPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _build_test_session()
        self.user = User(
            id=1,
            username="agent1",
            password_hash="hash",
            role=UserRole.AGENT,
        )
        self.contact = Contact(id=2, whatsapp_number="15551234567")
        self.conversation = Conversation(
            id=3,
            contact_id=self.contact.id,
            state=ConversationState.ASIGNADO,
            assigned_to=self.user.id,
        )
        self.session.add_all([self.user, self.contact, self.conversation])
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()

    def _extras_for_tmpdir(self, tmpdir: str) -> ExtrasConfig:
        base = get_extras_config()
        return replace(base, attachments_dir=tmpdir)

    def _patch_sqlite_ids(self):
        original_append_message = crud.append_message
        original_create_attachment = crud.create_attachment_metadata
        original_create_receipt = crud.create_message_receipt
        original_create_event = crud.create_conversation_event

        def append_message_with_id(*args, **kwargs):
            message = original_append_message(*args, **kwargs)
            if message.id is None:
                message.id = _next_id(args[0], Message)
            return message

        def create_attachment_with_id(*args, **kwargs):
            attachment = original_create_attachment(*args, **kwargs)
            if attachment.id is None:
                attachment.id = _next_id(args[0], AttachmentMetadata)
            return attachment

        def create_receipt_with_id(*args, **kwargs):
            receipt = original_create_receipt(*args, **kwargs)
            if receipt.id is None:
                receipt.id = _next_id(args[0], MessageReceipt)
            return receipt

        def create_event_with_id(*args, **kwargs):
            event = original_create_event(*args, **kwargs)
            if event.id is None:
                event.id = _next_id(args[0], ConversationEvent)
            return event

        return (
            patch("app.attachment_pipeline.crud.append_message", side_effect=append_message_with_id),
            patch(
                "app.attachment_pipeline.crud.create_attachment_metadata",
                side_effect=create_attachment_with_id,
            ),
            patch("app.attachment_pipeline.crud.create_message_receipt", side_effect=create_receipt_with_id),
            patch("app.attachment_pipeline.crud.create_conversation_event", side_effect=create_event_with_id),
        )

    def test_attachment_send_success_is_persisted(self) -> None:
        with TemporaryDirectory() as tmpdir:
            p1, p2, p3, p4 = self._patch_sqlite_ids()
            with p1, p2, p3, p4, patch(
                "app.attachment_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdir(tmpdir),
            ), patch("app.attachment_pipeline.upload_media", return_value="media-001"), patch(
                "app.attachment_pipeline.send_media_message",
                return_value=WhatsAppSendResponse(
                    message_id="wamid-001",
                    payload={"messages": [{"id": "wamid-001"}]},
                ),
            ):
                result = send_outbound_attachment(
                    self.session,
                    conversation_id=self.conversation.id,
                    to_number=self.contact.whatsapp_number,
                    actor_user_id=self.user.id,
                    original_filename="invoice.pdf",
                    reported_mime="application/pdf",
                    content=b"pdf-binary",
                    attachment_id="att-001",
                )
                self.session.flush()

        self.assertTrue(result.ok)
        self.assertEqual(result.status, AttachmentStatus.SENT)
        attachment = crud.get_attachment_by_attachment_id(self.session, attachment_id="att-001")
        self.assertIsNotNone(attachment)
        assert attachment is not None
        self.assertEqual(attachment.status, AttachmentStatus.SENT)
        self.assertIsNotNone(attachment.message_id)

    def test_retry_after_failed_send_is_deduped_and_transitions_to_sent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            p1, p2, p3, p4 = self._patch_sqlite_ids()
            with p1, p2, p3, p4, patch(
                "app.attachment_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdir(tmpdir),
            ), patch("app.attachment_pipeline.upload_media", return_value="media-001"), patch(
                "app.attachment_pipeline.send_media_message",
                side_effect=WhatsAppSendError("provider down"),
            ):
                first = send_outbound_attachment(
                    self.session,
                    conversation_id=self.conversation.id,
                    to_number=self.contact.whatsapp_number,
                    actor_user_id=self.user.id,
                    original_filename="voice-note.mp3",
                    reported_mime="audio/mpeg",
                    content=b"audio-1",
                    attachment_id="att-retry",
                )
                self.session.flush()

            p1, p2, p3, p4 = self._patch_sqlite_ids()
            with p1, p2, p3, p4, patch(
                "app.attachment_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdir(tmpdir),
            ), patch("app.attachment_pipeline.upload_media", return_value="media-002"), patch(
                "app.attachment_pipeline.send_media_message",
                return_value=WhatsAppSendResponse(
                    message_id="wamid-xyz",
                    payload={"messages": [{"id": "wamid-xyz"}]},
                ),
            ):
                second = send_outbound_attachment(
                    self.session,
                    conversation_id=self.conversation.id,
                    to_number=self.contact.whatsapp_number,
                    actor_user_id=self.user.id,
                    original_filename="voice-note.mp3",
                    reported_mime="audio/mpeg",
                    content=b"audio-2",
                    attachment_id="att-retry",
                )
                self.session.flush()

        self.assertFalse(first.ok)
        self.assertEqual(first.status, AttachmentStatus.FAILED)
        self.assertTrue(second.ok)
        self.assertEqual(second.status, AttachmentStatus.SENT)
        self.assertEqual(first.message_id, second.message_id)
        attachments_count = self.session.scalar(select(func.count(AttachmentMetadata.id)))
        messages_count = self.session.scalar(select(func.count(Message.id)))
        self.assertEqual(int(attachments_count or 0), 1)
        self.assertEqual(int(messages_count or 0), 1)

    def test_sent_attachment_retry_returns_existing_without_new_send(self) -> None:
        with TemporaryDirectory() as tmpdir:
            p1, p2, p3, p4 = self._patch_sqlite_ids()
            with p1, p2, p3, p4, patch(
                "app.attachment_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdir(tmpdir),
            ), patch("app.attachment_pipeline.upload_media", return_value="media-001"), patch(
                "app.attachment_pipeline.send_media_message",
                return_value=WhatsAppSendResponse(
                    message_id="wamid-sent",
                    payload={"messages": [{"id": "wamid-sent"}]},
                ),
            ):
                first = send_outbound_attachment(
                    self.session,
                    conversation_id=self.conversation.id,
                    to_number=self.contact.whatsapp_number,
                    actor_user_id=self.user.id,
                    original_filename="photo.jpg",
                    reported_mime="image/jpeg",
                    content=b"image",
                    attachment_id="att-sent",
                )
                self.session.flush()

            p1, p2, p3, p4 = self._patch_sqlite_ids()
            with p1, p2, p3, p4, patch(
                "app.attachment_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdir(tmpdir),
            ), patch(
                "app.attachment_pipeline.upload_media",
                side_effect=AssertionError("upload should not run for already-sent attachment"),
            ), patch(
                "app.attachment_pipeline.send_media_message",
                side_effect=AssertionError("send should not run for already-sent attachment"),
            ):
                second = send_outbound_attachment(
                    self.session,
                    conversation_id=self.conversation.id,
                    to_number=self.contact.whatsapp_number,
                    actor_user_id=self.user.id,
                    original_filename="photo.jpg",
                    reported_mime="image/jpeg",
                    content=b"image",
                    attachment_id="att-sent",
                )
                self.session.flush()

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.message_id, second.message_id)
        self.assertEqual(first.attachment_id, second.attachment_id)
        attachments_count = self.session.scalar(select(func.count(AttachmentMetadata.id)))
        self.assertEqual(int(attachments_count or 0), 1)


if __name__ == "__main__":
    unittest.main()
