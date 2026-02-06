# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed in latest chunk
- Task completed: T1.7 Implement hard delete + deletion event.
- Added `app/hard_delete.py` with admin-only hard delete orchestration for:
  - attachment file cleanup,
  - export artifact cleanup,
  - DB cleanup (messages, receipts, metadata, read states, conversation events, conversation row),
  - minimal deletion event creation.
- Added `conversation_deletion_events` model + migration:
  - `app/db/models.py`
  - `alembic/versions/20260206_02_add_conversation_deletion_events_table.py`
- Added CRUD helpers for deletion events in `app/db/crud.py`.
- Added admin endpoint `POST /conversations/{conversation_id}/hard-delete` in `app/api/conversations.py`.
- Added integration coverage in `tests/test_hard_delete.py`.

## Execution anchor
- Branch: `impl/whatsapp-frontdesk-extensions`.
- Current task in `TASKS.md`: T2.1.
- Progress: 8/13.

## Verification performed
- `.venv/bin/python -m unittest -v tests/test_hard_delete.py`
- `.venv/bin/python -m unittest -v tests/test_export_pipeline.py`
- `.venv/bin/python -m unittest -v tests/test_export_cleanup.py`
- `.venv/bin/python -m unittest -v tests/test_attachment_pipeline.py`

## Resume next
- Implement T2.1 reverse-proxy download/view authorization with `X-Accel-Redirect`.
- Add backend authorize endpoints for attachment/export downloads and document proxy config requirements.
- Keep known DB caveat in mind: full `alembic upgrade head` is still blocked by prior SQLite-incompatible migration `20260202_03`.
