# CHECKPOINT — whatsapp-frontdesk-extensions

Last updated: 2026-02-06

## Completed
- T0.1 align configs, roles, and feature flags.
- Added env/flag scaffolding in `app/config.py`.
- Documented env vars, flags, and role matrix in `docs/specs/whatsapp-frontdesk-extensions/CONFIG.md`.

## Current / Next
- Next task: T1.1 Implement attachment metadata model.
- Status: READY

## Important constraints
- Attachment/export storage roots are configurable via env (`ATTACHMENTS_DIR`, `EXPORTS_DIR`).
- Export retention uses `EXPORTS_TTL_DAYS` with default 7 days.
- Feature flags default disabled for controlled rollout by environment.

## Gotchas / Risks discovered
- Core currently models only `agent/admin`; `supervisor` must be introduced explicitly in later task scope.
- No stable automated test suite is currently runnable in this environment without extra setup.

## Safe resume instructions
- Continue on `impl/whatsapp-frontdesk-extensions`.
- Start with T1.1 schema/model work; preserve T0.1 env names and flag names.
