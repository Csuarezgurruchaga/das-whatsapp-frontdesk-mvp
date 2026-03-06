# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed in this chunk
- Started task `T4.1` (Release/rollout readiness).
- Added `docs/specs/whatsapp-frontdesk-extensions/DEPLOYMENT.md` with:
  - acceptance checklist template for A0-A7,
  - rollout checklist,
  - rollback procedure,
  - operator/admin short guide,
  - explicit sign-off record section.
- Updated `TASKS.md` execution notes to reflect current T4.1 state.

## Current status
- Status: IN_PROGRESS
- Current task: T4.1
- Progress: 12/13
- Remaining blocker: staging/on-prem acceptance execution + stakeholder sign-off.

## Constraints / risks
- Final T4.1 verification needs integrated runtime (NAS + reverse-proxy + SSO + seeded roles + WA creds).
- Keep reverse-proxy `X-Accel-Redirect` no-streaming contract unchanged.

## Safe resume
- Checkout `dev`.
- Execute local baseline checks:
  - `.venv/bin/python -m unittest discover -s tests -v`
  - `node --check app/static/app.js`
- Run `DEPLOYMENT.md` checklist in staging and fill evidence/sign-off fields.
- When sign-off is complete, mark `T4.1` done and set TASKS status to `DONE`.
