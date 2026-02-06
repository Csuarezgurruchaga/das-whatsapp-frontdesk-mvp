# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T2.2 Implement frontend attachments UI (composer + history + view/download).
- Added paperclip entrypoint and hidden file input in `app/static/index.html`.
- Implemented attachment upload flow in `app/static/app.js`:
  - pre-upload validation (MIME allowlist + per-type size caps),
  - optimistic `uploading` message,
  - final `sent/failed` refresh from backend.
- Added attachment bubble rendering and actions in `app/static/app.js`:
  - icon + filename + size + status,
  - `Ver` for PDF/PNG/JPG/JPEG/TXT,
  - `Descargar` for all attachment types.
- Added preview modal and attachment styling in `app/static/styles.css`.
- Fixed modal hidden-state override and wired missing attachment/modal listeners after interrupted session.

## Current / Next
- Next task: T2.3 Implement tipification UI (tags) + taxonomy admin UI.
- Status: READY

## Important constraints
- Backend must authorize with normal session, then delegate file serving via proxy (no app streaming).
- Keep current role model (`agent`, `admin`) unchanged until role-expansion tasks.

## Gotchas / Risks discovered
- Browser-level validation for T2.2 requires seeded conversations and authenticated UI session in staging/local.
- Existing SQLite migration caveat remains for full `alembic upgrade head` (`20260202_03` incompatibility).

## Safe resume instructions
- Checkout branch `impl/whatsapp-frontdesk-extensions`.
- Start from `TASKS.md` current task `T2.3`.
- Verify backend baseline with `.venv/bin/python -m unittest discover -s tests -v`.
- Verify frontend script syntax with `node --check app/static/app.js`.
