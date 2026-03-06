import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


class TestAlembicSqliteUpgrade(unittest.TestCase):
    def test_upgrade_head_completes_on_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "alembic-check.db"
            database_url = f"sqlite:///{db_path}"
            previous_database_url = os.environ.get("DATABASE_URL")
            os.environ["DATABASE_URL"] = database_url

            try:
                completed = subprocess.run(
                    [sys.executable, "-m", "alembic", "upgrade", "head"],
                    cwd=Path(__file__).resolve().parents[1],
                    env=os.environ.copy(),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if completed.returncode != 0:
                    self.fail(
                        "alembic upgrade head failed:\n"
                        f"stdout:\n{completed.stdout}\n"
                        f"stderr:\n{completed.stderr}"
                    )

                engine = create_engine(database_url, future=True)
                inspector = inspect(engine)
                tables = set(inspector.get_table_names())
                expected_tables = {
                    "alembic_version",
                    "users",
                    "contacts",
                    "conversations",
                    "messages",
                    "conversation_read_states",
                    "conversation_events",
                    "message_receipts",
                    "user_sessions",
                    "attachment_metadata",
                    "conversation_deletion_events",
                    "taxonomy_tags",
                    "conversation_tags",
                }
                self.assertEqual(expected_tables, tables)

                with engine.connect() as connection:
                    version = connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                self.assertEqual(version, "20260305_01")
                engine.dispose()
            finally:
                if previous_database_url is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous_database_url
