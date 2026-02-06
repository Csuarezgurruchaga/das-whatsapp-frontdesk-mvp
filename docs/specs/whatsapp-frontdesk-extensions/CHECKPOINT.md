# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T3.1 Add logs/metrics and operator-facing errors.
- Added attachment send observability in `app/attachment_pipeline.py`:
  - success/failure counters (`get_attachment_send_counters`, `reset_attachment_send_counters`),
  - structured success/failure logs for send attempts.
- Added proxy observability logs in `app/api/conversations.py`:
  - auth denial logs for attachment/export authorization endpoints,
  - missing file logs for attachment/export reverse-proxy serving paths.
- Improved operator-facing composer errors:
  - backend sends explicit WhatsApp send-failure details for text/attachment send failures,
  - frontend now surfaces backend detail for text send and keeps explicit fallback for attachment send.
- Added regression coverage:
  - `tests/test_attachment_pipeline.py` asserts send counters,
  - `tests/test_proxy_download_authorization.py` asserts denial/missing-file logging.

## Current / Next
- Next task: T4.1 Staging validation + rollout checklist.
- Status: READY

## Important constraints
- Keep Extras strictly behind existing role/permission checks.
- Preserve non-streaming proxy download behavior implemented in T2.1.

## Gotchas / Risks discovered
- Full browser/staging validation still requires authenticated seeded users and on-prem-like infra (NAS + proxy + SSO).
- Existing SQLite migration caveat remains for full `alembic upgrade head` (`20260202_03` incompatibility).

## Safe resume instructions
- Checkout branch `impl/whatsapp-frontdesk-extensions`.
- Start from `TASKS.md` current task `T4.1`.
- Verify backend baseline with `.venv/bin/python -m unittest discover -s tests -v`.
- Verify frontend script syntax with `node --check app/static/app.js`.
