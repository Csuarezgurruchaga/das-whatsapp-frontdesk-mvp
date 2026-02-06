# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06
- Completed: `T0.1`, `T1.1`, `T1.2`.
- Branch: `impl/whatsapp-frontdesk-extensions`.
- Status: `READY_FOR_T1.3`.

## What changed in T1.2
- Added `app/attachments.py` with reusable helpers for `safe(truncate(filename))`, MIME allowlist/extension fallback, and size validation.
- Enforced constants: 100MB global limit, MIME allowlist from SPEC, per-type caps (image 5MB, audio/video 16MB, document 100MB).
- Added unit tests in `tests/test_attachment_validation.py` covering separators, `..`, long names, Unicode NFC, octet-stream fallback, allowlist rejection, and per-type size caps.

## Next task
- `T1.3`: store binaries under `ATTACHMENTS_DIR/<conversation_id>/<attachment_id>_<safe_filename>` and persist matching `storage_relpath`.
- Reuse `app/attachments.py` helpers; do not duplicate sanitization/validation rules.

## Known constraints / gotchas
- Existing migration `20260202_03` is SQLite-incompatible (`ALTER COLUMN ... DROP NOT NULL`), so full `alembic upgrade head` may fail on SQLite.
- Preserve T1.1 contracts: required metadata fields, unique `attachment_id`, indexes on `conversation_id` and `message_id`.

## Verification proof
- `python3 -m unittest -v tests/test_attachment_validation.py`
