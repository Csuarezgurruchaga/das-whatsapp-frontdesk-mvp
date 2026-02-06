# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T0.1 Align configs, roles, and feature flags.
- T1.1 Implement attachment metadata model.
- T1.2 Implement `safe(truncate(filename))` + MIME validation.
- T1.3 Implement attachment binary storage on NAS.

## Current / Next
- Next task: T1.4 Implement attachment upload + send pipeline (WhatsApp native media).
- Status: READY.

## Important constraints
- Keep storage path format `ATTACHMENTS_DIR/<conversation_id>/<attachment_id>_<safe_filename>`.
- Reuse `app/attachments.py` for sanitization and MIME/size validation; do not duplicate rules.
- Keep metadata `storage_relpath` aligned with on-disk path for later `X-Accel-Redirect`.

## Gotchas / Risks discovered
- Full `alembic upgrade head` still fails on SQLite because prior migration `20260202_03` uses unsupported `ALTER COLUMN ... DROP NOT NULL`.
- SQLite tests require explicit IDs for `BigInteger` PK in `attachment_metadata` (test setup sets `attachment.id` before flush).

## Safe resume instructions
- Continue from branch `impl/whatsapp-frontdesk-extensions`.
- Implement T1.4 using `store_attachment_binary` from `app/attachment_storage.py` and existing metadata CRUD.
- Re-run: `.venv/bin/python -m unittest -v tests/test_attachment_storage.py tests/test_attachment_validation.py`.
