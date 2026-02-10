from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.attachment_storage import (
    build_attachment_storage_relpath,
    read_attachment_binary,
    store_attachment_binary,
)
from app.db import crud
from app.db.base import Base
from app.db.models import (
    AttachmentStatus,
    Contact,
    Conversation,
    ConversationState,
    User,
    UserRole,
)


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


class TestAttachmentStorage(unittest.TestCase):
    def test_build_relpath_uses_conversation_folder_and_safe_filename(self) -> None:
        relpath = build_attachment_storage_relpath(
            conversation_id=42,
            attachment_id="att-123",
            original_filename="../unsafe\\name?.pdf",
        )
        self.assertTrue(relpath.startswith("42/att-123_"))
        self.assertNotIn("..", relpath)
        self.assertNotIn("\\", relpath)
        self.assertTrue(relpath.endswith(".pdf"))

    def test_store_and_read_attachment_binary_roundtrip(self) -> None:
        with TemporaryDirectory() as tmpdir:
            relpath = store_attachment_binary(
                attachments_dir=tmpdir,
                conversation_id=7,
                attachment_id="att-xyz",
                original_filename="report final.txt",
                content=b"payload-content",
            )
            stored_path = Path(tmpdir) / relpath
            self.assertTrue(stored_path.exists())
            self.assertEqual(
                read_attachment_binary(attachments_dir=tmpdir, storage_relpath=relpath),
                b"payload-content",
            )

    def test_store_attachment_cleans_temp_file_when_replace_fails(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch("app.attachment_storage.os.replace", side_effect=PermissionError):
                with self.assertRaises(PermissionError):
                    store_attachment_binary(
                        attachments_dir=tmpdir,
                        conversation_id=9,
                        attachment_id="att-fail",
                        original_filename="invoice.pdf",
                        content=b"123",
                    )

            conversation_dir = Path(tmpdir) / "9"
            if conversation_dir.exists():
                self.assertEqual(list(conversation_dir.iterdir()), [])

    def test_read_rejects_path_escape(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                read_attachment_binary(
                    attachments_dir=tmpdir,
                    storage_relpath="../outside.txt",
                )

    def test_storage_relpath_persists_in_attachment_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with _build_test_session() as session:
                user = User(
                    id=1,
                    username="agent1",
                    password_hash="hash",
                    role=UserRole.AGENT,
                )
                contact = Contact(id=2, whatsapp_number="15550000001")
                conversation = Conversation(
                    id=3,
                    contact_id=contact.id,
                    state=ConversationState.CHATBOT,
                )
                session.add_all([user, contact, conversation])
                session.flush()

                relpath = store_attachment_binary(
                    attachments_dir=tmpdir,
                    conversation_id=conversation.id,
                    attachment_id="att-001",
                    original_filename="recording.mp3",
                    content=b"audio-data",
                )

                attachment = crud.create_attachment_metadata(
                    session,
                    conversation_id=conversation.id,
                    message_id=None,
                    attachment_id="att-001",
                    original_filename="recording.mp3",
                    mime="audio/mpeg",
                    size_bytes=10,
                    storage_relpath=relpath,
                    status=AttachmentStatus.UPLOADING,
                    created_by=user.id,
                )
                attachment.id = 10
                session.flush()

                self.assertEqual(attachment.storage_relpath, relpath)
                self.assertTrue((Path(tmpdir) / relpath).exists())


if __name__ == "__main__":
    unittest.main()
