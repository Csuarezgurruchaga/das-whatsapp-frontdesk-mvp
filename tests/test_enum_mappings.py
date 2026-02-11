from __future__ import annotations

import unittest

from app.db.models import AttachmentMetadata


class TestEnumMappings(unittest.TestCase):
    def test_attachment_status_uses_lowercase_values(self) -> None:
        enums = AttachmentMetadata.__table__.c.status.type.enums
        self.assertEqual(set(enums), {"uploading", "sent", "failed"})

