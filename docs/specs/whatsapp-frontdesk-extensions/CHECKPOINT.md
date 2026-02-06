# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed in latest chunk
- Task completed: T1.6 Implement exports TTL cleanup.
- Added `app/export_cleanup.py` with deterministic TTL cleanup based on file mtime.
- Cleanup now targets only valid export ZIP naming (`conversation-<conversation_id>-<export_id>.zip`) to avoid deleting unrelated files.
- Added dry-run mode (`python -m app.export_cleanup --dry-run`) for safe staging validation.
- Empty per-conversation export directories are removed after cleanup when they become empty.
- Added coverage in `tests/test_export_cleanup.py` for expired deletion, dry-run behavior, and non-export ZIP safety.

## Execution anchor
- Branch: `impl/whatsapp-frontdesk-extensions`.
- Current task in `TASKS.md`: T1.7.
- Progress: 7/13.

## Verification performed
- `.venv/bin/python -m unittest -v tests/test_export_cleanup.py`
- `.venv/bin/python -m unittest -v tests/test_export_pipeline.py`

## Resume next
- Implement T1.7 hard delete + deletion event.
- Reuse cleanup/export safety constraints for file removal operations in hard-delete flow.
- Keep known DB caveat in mind: full `alembic upgrade head` is still blocked by prior SQLite-incompatible migration `20260202_03`.
