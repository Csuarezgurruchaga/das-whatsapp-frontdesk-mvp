from __future__ import annotations

import unittest

from app.attachments import (
    AUDIO_MAX_UPLOAD_BYTES,
    IMAGE_MAX_UPLOAD_BYTES,
    MAX_FILENAME_BASE_CHARS,
    MAX_UPLOAD_BYTES,
    VIDEO_MAX_UPLOAD_BYTES,
    resolve_attachment_mime,
    sanitize_attachment_filename,
    validate_attachment,
    validate_attachment_size,
)


class TestAttachmentValidation(unittest.TestCase):
    def test_sanitize_removes_separators_and_path_traversal(self) -> None:
        sanitized = sanitize_attachment_filename("../unsafe\\path/../../invoice?.pdf")
        self.assertNotIn("/", sanitized)
        self.assertNotIn("\\", sanitized)
        self.assertNotIn("..", sanitized)
        self.assertTrue(sanitized.endswith(".pdf"))

    def test_sanitize_truncates_base_name_preserving_extension(self) -> None:
        very_long = ("a" * 300) + ".docx"
        sanitized = sanitize_attachment_filename(very_long)
        base, extension = sanitized.rsplit(".", 1)
        self.assertEqual(len(base), MAX_FILENAME_BASE_CHARS)
        self.assertEqual(extension, "docx")

    def test_sanitize_normalizes_unicode_to_nfc(self) -> None:
        sanitized = sanitize_attachment_filename("Cafe\u0301.png")
        self.assertEqual(sanitized, "Café.png")

    def test_resolve_mime_uses_extension_fallback_for_octet_stream(self) -> None:
        resolved = resolve_attachment_mime(
            filename="reporte-final.pdf",
            reported_mime="application/octet-stream",
        )
        self.assertEqual(resolved, "application/pdf")

    def test_resolve_mime_uses_extension_fallback_for_empty_mime(self) -> None:
        resolved = resolve_attachment_mime(
            filename="foto.jpg",
            reported_mime="",
        )
        self.assertEqual(resolved, "image/jpeg")

    def test_resolve_mime_rejects_unsupported_reported_mime(self) -> None:
        with self.assertRaises(ValueError):
            resolve_attachment_mime(
                filename="archive.zip",
                reported_mime="application/zip",
            )

    def test_per_type_size_caps(self) -> None:
        with self.assertRaises(ValueError):
            validate_attachment_size(
                size_bytes=IMAGE_MAX_UPLOAD_BYTES + 1,
                mime="image/jpeg",
            )

        with self.assertRaises(ValueError):
            validate_attachment_size(
                size_bytes=AUDIO_MAX_UPLOAD_BYTES + 1,
                mime="audio/mpeg",
            )

        with self.assertRaises(ValueError):
            validate_attachment_size(
                size_bytes=VIDEO_MAX_UPLOAD_BYTES + 1,
                mime="video/mp4",
            )

        with self.assertRaises(ValueError):
            validate_attachment_size(
                size_bytes=MAX_UPLOAD_BYTES + 1,
                mime="application/pdf",
            )

    def test_validate_attachment_happy_path(self) -> None:
        result = validate_attachment(
            filename="  reporte final 2026.PDF  ",
            reported_mime="application/pdf",
            size_bytes=1024,
        )
        self.assertEqual(result.mime, "application/pdf")
        self.assertEqual(result.media_kind, "document")
        self.assertEqual(result.size_bytes, 1024)
        self.assertEqual(result.safe_filename, "reporte_final_2026.PDF")


if __name__ == "__main__":
    unittest.main()
