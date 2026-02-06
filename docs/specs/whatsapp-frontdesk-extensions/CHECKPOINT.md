# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T2.3 Implement tipification UI (tags) + taxonomy admin UI.
- Added taxonomy/tag persistence and APIs:
  - new `taxonomy_tags` + `conversation_tags` models/migration,
  - conversation tag assignment endpoint (`PUT /conversations/{id}/tags`),
  - taxonomy admin endpoints (list/create/update with role gating).
- Added `supervisor` role support for taxonomy read-only behavior.
- Extended conversation detail payload with `tags` + `available_tags`.
- Implemented frontend tipification and taxonomy admin UX:
  - detail-panel tag selector for operator/admin,
  - taxonomy modal with admin create/rename/archive,
  - supervisor read-only taxonomy list UI.
- Added regression coverage in `tests/test_taxonomy_and_tags.py`.

## Current / Next
- Next task: T3.1 Add logs/metrics and operator-facing errors.
- Status: READY

## Important constraints
- Keep Extras strictly behind existing role/permission checks.
- Preserve non-streaming proxy download behavior implemented in T2.1.

## Gotchas / Risks discovered
- Full browser validation for T2.3 still requires authenticated seeded users (`admin`, `agent`, `supervisor`).
- Existing SQLite migration caveat remains for full `alembic upgrade head` (`20260202_03` incompatibility).

## Safe resume instructions
- Checkout branch `impl/whatsapp-frontdesk-extensions`.
- Start from `TASKS.md` current task `T3.1`.
- Verify backend baseline with `.venv/bin/python -m unittest discover -s tests -v`.
- Verify frontend script syntax with `node --check app/static/app.js`.
