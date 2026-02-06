from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import conversations
from app.config import get_extras_config
from app.db.base import Base
from app.db.models import (
    AttachmentMetadata,
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


class TestProxyDownloadAuthorization(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _build_test_session()
        self.tempdir = TemporaryDirectory()
        self.attachments_dir = Path(self.tempdir.name) / "attachments"
        self.exports_dir = Path(self.tempdir.name) / "exports"
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        base_config = get_extras_config()
        self._config_patch = patch(
            "app.api.conversations.get_extras_config",
            return_value=replace(
                base_config,
                attachments_dir=str(self.attachments_dir),
                exports_dir=str(self.exports_dir),
            ),
        )
        self._config_patch.start()

        self.admin = User(
            id=1,
            username="admin",
            password_hash="hash",
            role=UserRole.ADMIN,
        )
        self.agent = User(
            id=2,
            username="agent",
            password_hash="hash",
            role=UserRole.AGENT,
        )
        self.contact = Contact(
            id=10,
            whatsapp_number="15550001234",
            display_name="Test Contact",
        )
        self.conversation = Conversation(
            id=200,
            contact_id=self.contact.id,
            state=ConversationState.ASIGNADO,
            assigned_to=self.agent.id,
        )
        self.session.add_all([self.admin, self.agent, self.contact, self.conversation])
        self.session.flush()

        self.attachment_pdf = AttachmentMetadata(
            id=300,
            conversation_id=self.conversation.id,
            message_id=None,
            attachment_id="att-pdf",
            original_filename="invoice.pdf",
            mime="application/pdf",
            size_bytes=7,
            storage_relpath="200/att-pdf_invoice.pdf",
            status=AttachmentStatus.SENT,
            created_by=self.agent.id,
        )
        self.attachment_doc = AttachmentMetadata(
            id=301,
            conversation_id=self.conversation.id,
            message_id=None,
            attachment_id="att-doc",
            original_filename="report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=9,
            storage_relpath="200/att-doc_report.docx",
            status=AttachmentStatus.SENT,
            created_by=self.agent.id,
        )
        self.session.add_all([self.attachment_pdf, self.attachment_doc])
        self.session.commit()

        pdf_path = self.attachments_dir / "200" / "att-pdf_invoice.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"pdfdata")
        doc_path = self.attachments_dir / "200" / "att-doc_report.docx"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_bytes(b"docxdata")

        export_path = self.exports_dir / "200" / "conversation-200-exp001.zip"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_bytes(b"zipdata")

    def tearDown(self) -> None:
        self.session.close()
        self._config_patch.stop()
        self.tempdir.cleanup()

    def test_attachment_download_returns_accel_headers(self) -> None:
        response = conversations.authorize_attachment_download(
            conversation_id=200,
            attachment_id="att-pdf",
            current_user=self.agent,
            db=self.session,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("x-accel-redirect"),
            "/_internal/attachments/200/att-pdf_invoice.pdf",
        )
        self.assertEqual(response.headers.get("content-type"), "application/pdf")
        self.assertIn("attachment;", response.headers.get("content-disposition", ""))
        self.assertEqual(response.body, b"")

    def test_attachment_view_rejects_non_viewable_mime(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            conversations.authorize_attachment_view(
                conversation_id=200,
                attachment_id="att-doc",
                current_user=self.agent,
                db=self.session,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Attachment MIME is not viewable")

    def test_attachment_view_returns_inline_disposition(self) -> None:
        response = conversations.authorize_attachment_view(
            conversation_id=200,
            attachment_id="att-pdf",
            current_user=self.agent,
            db=self.session,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("x-accel-redirect"),
            "/_internal/attachments/200/att-pdf_invoice.pdf",
        )
        self.assertIn("inline;", response.headers.get("content-disposition", ""))

    def test_export_download_requires_admin(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            conversations.authorize_export_download(
                conversation_id=200,
                export_id="exp001",
                current_user=self.agent,
                db=self.session,
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Forbidden")

    def test_export_download_returns_accel_headers_for_admin(self) -> None:
        response = conversations.authorize_export_download(
            conversation_id=200,
            export_id="exp001",
            current_user=self.admin,
            db=self.session,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("x-accel-redirect"),
            "/_internal/exports/200/conversation-200-exp001.zip",
        )
        self.assertEqual(response.headers.get("content-type"), "application/zip")


if __name__ == "__main__":
    unittest.main()
