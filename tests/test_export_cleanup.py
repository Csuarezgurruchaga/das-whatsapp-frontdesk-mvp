from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from app.export_cleanup import cleanup_expired_exports


def _write_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        archive.writestr("transcript.json", "{}")


def _set_mtime(path: Path, moment: datetime) -> None:
    timestamp = moment.timestamp()
    os.utime(path, (timestamp, timestamp))


class TestExportCleanup(unittest.TestCase):
    def test_cleanup_deletes_expired_exports_and_removes_empty_conversation_dirs(self) -> None:
        with TemporaryDirectory() as exports_dir:
            old_file = (
                Path(exports_dir) / "3" / "conversation-3-exp-old.zip"
            )
            recent_file = (
                Path(exports_dir) / "4" / "conversation-4-exp-recent.zip"
            )
            _write_zip(old_file)
            _write_zip(recent_file)
            _set_mtime(old_file, datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc))
            _set_mtime(recent_file, datetime(2026, 2, 5, 12, 0, tzinfo=timezone.utc))

            result = cleanup_expired_exports(
                now=datetime(2026, 2, 6, 12, 0, tzinfo=timezone.utc),
                exports_dir=exports_dir,
                exports_ttl_days=7,
            )

            self.assertEqual(result.scanned_export_files, 2)
            self.assertEqual(result.expired_export_files, 1)
            self.assertEqual(result.kept_export_files, 1)
            self.assertEqual(result.deleted_export_files, 1)
            self.assertEqual(result.deleted_relpaths, ("3/conversation-3-exp-old.zip",))
            self.assertEqual(result.removed_directories, 1)
            self.assertFalse(old_file.exists())
            self.assertFalse((Path(exports_dir) / "3").exists())
            self.assertTrue(recent_file.exists())

    def test_cleanup_dry_run_keeps_files(self) -> None:
        with TemporaryDirectory() as exports_dir:
            old_file = Path(exports_dir) / "7" / "conversation-7-exp-dry.zip"
            _write_zip(old_file)
            _set_mtime(old_file, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))

            result = cleanup_expired_exports(
                now=datetime(2026, 2, 6, 12, 0, tzinfo=timezone.utc),
                dry_run=True,
                exports_dir=exports_dir,
                exports_ttl_days=7,
            )

            self.assertEqual(result.expired_export_files, 1)
            self.assertEqual(result.deleted_export_files, 0)
            self.assertEqual(result.removed_directories, 0)
            self.assertTrue(old_file.exists())
            self.assertTrue((Path(exports_dir) / "7").exists())

    def test_cleanup_ignores_non_export_zip_files(self) -> None:
        with TemporaryDirectory() as exports_dir:
            valid_export = Path(exports_dir) / "8" / "conversation-8-exp-valid.zip"
            non_export_zip = Path(exports_dir) / "8" / "other-archive.zip"
            _write_zip(valid_export)
            _write_zip(non_export_zip)
            _set_mtime(valid_export, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))
            _set_mtime(non_export_zip, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))

            result = cleanup_expired_exports(
                now=datetime(2026, 2, 6, 12, 0, tzinfo=timezone.utc),
                exports_dir=exports_dir,
                exports_ttl_days=7,
            )

            self.assertEqual(result.scanned_export_files, 1)
            self.assertEqual(result.expired_export_files, 1)
            self.assertEqual(result.deleted_export_files, 1)
            self.assertEqual(result.skipped_non_export_files, 1)
            self.assertFalse(valid_export.exists())
            self.assertTrue(non_export_zip.exists())
            self.assertTrue((Path(exports_dir) / "8").exists())


if __name__ == "__main__":
    unittest.main()
