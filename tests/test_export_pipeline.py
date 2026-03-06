from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.attachment_storage import store_attachment_binary
from app.config import ExtrasConfig, get_extras_config
from app.db import crud
from app.db.base import Base
from app.db.models import (
    AttachmentMetadata,
    AttachmentStatus,
    Contact,
    Conversation,
    ConversationState,
    Message,
    MessageDirection,
    SenderType,
    User,
    UserRole,
)
from app.export_pipeline import generate_conversation_export_zip


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


def _next_id(session: Session, model: type) -> int:
    with session.no_autoflush:
        value = session.scalar(select(func.coalesce(func.max(model.id), 0)))
    return int(value or 0) + 1


class TestExportPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _build_test_session()
        self.user = User(
            id=1,
            username="admin1",
            password_hash="hash",
            role=UserRole.ADMIN,
        )
        self.contact = Contact(id=2, whatsapp_number="15550000002")
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

    def _extras_for_tmpdirs(self, *, attachments_dir: str, exports_dir: str) -> ExtrasConfig:
        base = get_extras_config()
        return replace(base, attachments_dir=attachments_dir, exports_dir=exports_dir)

    def _append_message(self, *, text: str) -> Message:
        message = crud.append_message(
            self.session,
            conversation_id=self.conversation.id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.AGENT,
            text=text,
        )
        if message.id is None:
            message.id = _next_id(self.session, Message)
        return message

    def _create_attachment_metadata(
        self,
        *,
        message_id: int,
        attachment_id: str,
        original_filename: str,
        storage_relpath: str,
        size_bytes: int,
    ) -> AttachmentMetadata:
        attachment = crud.create_attachment_metadata(
            self.session,
            conversation_id=self.conversation.id,
            message_id=message_id,
            attachment_id=attachment_id,
            original_filename=original_filename,
            mime="application/pdf",
            size_bytes=size_bytes,
            storage_relpath=storage_relpath,
            status=AttachmentStatus.SENT,
            created_by=self.user.id,
        )
        if attachment.id is None:
            attachment.id = _next_id(self.session, AttachmentMetadata)
        return attachment

    def test_generate_export_zip_includes_transcript_and_attachment_binary(self) -> None:
        with TemporaryDirectory() as attachments_dir, TemporaryDirectory() as exports_dir:
            message = self._append_message(text="[attachment] invoice.pdf")
            relpath = store_attachment_binary(
                attachments_dir=attachments_dir,
                conversation_id=self.conversation.id,
                attachment_id="att-001",
                original_filename="../unsafe\\invoice?.pdf",
                content=b"pdf-bytes",
            )
            self._create_attachment_metadata(
                message_id=message.id,
                attachment_id="att-001",
                original_filename="../unsafe\\invoice?.pdf",
                storage_relpath=relpath,
                size_bytes=len(b"pdf-bytes"),
            )
            self.session.flush()

            with patch(
                "app.export_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdirs(
                    attachments_dir=attachments_dir,
                    exports_dir=exports_dir,
                ),
            ):
                result = generate_conversation_export_zip(
                    self.session,
                    conversation_id=self.conversation.id,
                    export_id="exp001",
                    now=datetime(2026, 2, 6, 18, 0, tzinfo=timezone.utc),
                )

            zip_path = Path(result.absolute_path)
            self.assertTrue(zip_path.exists())
            self.assertEqual(stat.S_IMODE(zip_path.stat().st_mode), 0o644)
            self.assertEqual(
                result.storage_relpath,
                f"{self.conversation.id}/conversation-{self.conversation.id}-exp001.zip",
            )
            self.assertEqual(result.attachment_count, 1)
            self.assertEqual(result.missing_attachments, 0)

            with ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                self.assertIn("transcript.json", names)
                attachment_entries = [name for name in names if name.startswith("attachments/")]
                self.assertEqual(len(attachment_entries), 1)
                attachment_entry = attachment_entries[0]
                self.assertNotIn("..", attachment_entry)
                self.assertNotIn("\\", attachment_entry)
                self.assertEqual(archive.read(attachment_entry), b"pdf-bytes")
                transcript = json.loads(archive.read("transcript.json"))

            self.assertEqual(transcript["conversation_id"], self.conversation.id)
            self.assertEqual(transcript["export_id"], "exp001")
            self.assertEqual(transcript["message_count"], 1)
            self.assertEqual(transcript["attachment_count"], 1)
            self.assertEqual(transcript["messages"][0]["attachment_ids"], ["att-001"])
            self.assertTrue(transcript["attachments"][0]["included_in_zip"])
            self.assertIsNone(transcript["attachments"][0]["warning"])

    def test_generate_export_zip_records_warning_for_missing_attachment_binary(self) -> None:
        with TemporaryDirectory() as attachments_dir, TemporaryDirectory() as exports_dir:
            message = self._append_message(text="[attachment] missing.pdf")
            self._create_attachment_metadata(
                message_id=message.id,
                attachment_id="att-missing",
                original_filename="missing.pdf",
                storage_relpath=f"{self.conversation.id}/att-missing_missing.pdf",
                size_bytes=123,
            )
            self.session.flush()

            with patch(
                "app.export_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdirs(
                    attachments_dir=attachments_dir,
                    exports_dir=exports_dir,
                ),
            ):
                result = generate_conversation_export_zip(
                    self.session,
                    conversation_id=self.conversation.id,
                    export_id="exp002",
                )

            with ZipFile(result.absolute_path) as archive:
                names = set(archive.namelist())
                self.assertEqual(names, {"transcript.json"})
                transcript = json.loads(archive.read("transcript.json"))

            self.assertEqual(result.missing_attachments, 1)
            self.assertEqual(transcript["attachments"][0]["attachment_id"], "att-missing")
            self.assertFalse(transcript["attachments"][0]["included_in_zip"])
            self.assertIn("missing", transcript["attachments"][0]["warning"])

    def test_generate_export_zip_rejects_unknown_conversation(self) -> None:
        with TemporaryDirectory() as attachments_dir, TemporaryDirectory() as exports_dir:
            with patch(
                "app.export_pipeline.get_extras_config",
                return_value=self._extras_for_tmpdirs(
                    attachments_dir=attachments_dir,
                    exports_dir=exports_dir,
                ),
            ):
                with self.assertRaisesRegex(ValueError, "conversation not found"):
                    generate_conversation_export_zip(
                        self.session,
                        conversation_id=99999,
                        export_id="exp003",
                    )


if __name__ == "__main__":
    unittest.main()
