# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T2.1 Implement reverse-proxy download/view authorization with `X-Accel-Redirect`.
- Added backend authorization endpoints in `app/api/conversations.py`:
  - attachment download/view by `attachment_id`
  - export download by `export_id`
- Added proxy deployment notes in `docs/specs/whatsapp-frontdesk-extensions/PROXY.md`.
- Added test coverage in `tests/test_proxy_download_authorization.py`.

## Current / Next
- Next task: T2.2 Implement frontend attachments UI (composer + history + view/download).
- Status: READY

## Important constraints
- Backend must authorize with normal session, then delegate file serving via proxy (no app streaming).
- Keep current role model (`agent`, `admin`) unchanged until role-expansion tasks.

## Gotchas / Risks discovered
- This environment lacks `httpx`, so API-route checks were verified through direct endpoint function tests.
- Existing SQLite migration caveat remains for full `alembic upgrade head` (`20260202_03` incompatibility).

## Safe resume instructions
- Checkout branch `impl/whatsapp-frontdesk-extensions`.
- Start from `TASKS.md` current task `T2.2`.
- Verify baseline with `.venv/bin/python -m unittest discover -s tests -v`.
