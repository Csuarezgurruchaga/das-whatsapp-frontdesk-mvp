# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed in latest chunk
- Task completed: T1.5 Implement export ZIP generation (on-demand).
- Added `app/export_pipeline.py` to generate per-conversation ZIP exports under `EXPORTS_DIR`.
- Export ZIP now includes `transcript.json` + available attachment binaries; missing binaries are recorded as warnings in transcript metadata.
- Added coverage in `tests/test_export_pipeline.py` for happy path, missing attachment binary, and unknown conversation.

## Execution anchor
- Branch: `impl/whatsapp-frontdesk-extensions`.
- Current task in `TASKS.md`: T1.6.
- Progress: 6/13.

## Verification performed
- `.venv/bin/python -m unittest -v tests/test_export_pipeline.py`
- `.venv/bin/python -m unittest -v tests/test_attachment_pipeline.py tests/test_attachment_storage.py tests/test_attachment_validation.py`

## Resume next
- Implement T1.6 exports TTL cleanup using `EXPORTS_DIR` and `EXPORTS_TTL_DAYS`.
- Preserve export layout introduced in T1.5: `<conversation_id>/conversation-<conversation_id>-<export_id>.zip`.
- Keep known DB caveat in mind: full `alembic upgrade head` is still blocked by prior SQLite-incompatible migration `20260202_03`.
