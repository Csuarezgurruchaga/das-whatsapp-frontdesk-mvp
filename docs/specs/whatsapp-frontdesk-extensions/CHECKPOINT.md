# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T0.1 align configs, roles, and feature flags.
- T1.1 implement attachment metadata model (schema/model + CRUD).
- Added `AttachmentMetadata` + `AttachmentStatus` in `app/db/models.py`.
- Added CRUD helpers in `app/db/crud.py`: create/get/list/get_or_create by `attachment_id`.
- Added migration `alembic/versions/20260206_01_add_attachment_metadata_table.py`.

## Current / Next
- Next task: T1.2 Implement `safe(truncate(filename))` + MIME validation.
- Status: READY_FOR_T1.2

## Important constraints
- Attachment/export storage roots are configurable via env (`ATTACHMENTS_DIR`, `EXPORTS_DIR`).
- Export retention uses `EXPORTS_TTL_DAYS` with default 7 days.
- Feature flags default disabled for controlled rollout by environment.

## Gotchas / Risks discovered
- Core currently models only `agent/admin`; `supervisor` must be introduced explicitly in later task scope.
- Existing migration `20260202_03` is not SQLite-compatible (`ALTER COLUMN ... DROP NOT NULL`), so full `alembic upgrade head` fails on SQLite.
- T1.1 behavior was verified via isolated SQLAlchemy roundtrip using in-memory SQLite (`Base.metadata.create_all`) instead.

## Safe resume instructions
- Continue on `impl/whatsapp-frontdesk-extensions`.
- Start with T1.2 library helpers for filename sanitization and MIME/extension validation.
- Preserve T1.1 contracts: required metadata fields, unique `attachment_id`, and indexes on `conversation_id` + `message_id`.
