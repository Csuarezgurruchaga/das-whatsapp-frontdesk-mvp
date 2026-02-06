# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T0.1 Align configs, roles, and feature flags.
- T1.1 Implement attachment metadata model.
- T1.2 Implement `safe(truncate(filename))` + MIME validation.
- T1.3 Implement attachment binary storage on NAS.
- T1.4 Implement attachment upload + send pipeline (WhatsApp native media).

## Current / Next
- Next task: T1.5 Implement export ZIP generation (on-demand).
- Status: READY.

## Important constraints
- Keep storage path format `ATTACHMENTS_DIR/<conversation_id>/<attachment_id>_<safe_filename>`.
- Keep upload validation strictly aligned to `app/attachments.py` (allowlist + extension fallback + per-type caps).
- Attachments are immutable and retry/idempotency is keyed by `attachment_id` (dedupe existing `SENT`; retry `FAILED`).

## Gotchas / Risks discovered
- Full `alembic upgrade head` still fails on SQLite because prior migration `20260202_03` uses unsupported `ALTER COLUMN ... DROP NOT NULL`.
- SQLite tests still require explicit IDs for `BigInteger` PK entities (patched in tests for message/attachment/receipt/event).
- New multipart upload endpoint requires `python-multipart` in `.venv`.

## Safe resume instructions
- Continue from branch `impl/whatsapp-frontdesk-extensions`.
- Start T1.5 from current backend artifacts: `app/attachment_pipeline.py`, `app/attachment_storage.py`, and `attachment_metadata.storage_relpath`.
- Re-run: `.venv/bin/python -m unittest -v tests/test_attachment_pipeline.py tests/test_attachment_storage.py tests/test_attachment_validation.py`.
