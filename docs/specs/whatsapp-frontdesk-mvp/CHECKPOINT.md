# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-02

## Completed
- T0.1 documented config conventions (env vars + reverse proxy + webhook URL)
- T0.2 validated bot.yaml and added local config artifact
- T1.1 core data model + Alembic baseline migration + CRUD access layer
- T1.2 audit events + message receipts tables and CRUD helpers
- T1.3 session auth (login/logout) + authorization guards + sessions table
- T1.4 handoff state transitions (take/reassign/close) + audit events

## Current / Next
- Next task: T1.5 bot engine (YAML-driven) + EN_ESPERA auto-messages
- Status: READY

## Important constraints
- Implement only tasks defined in docs/specs/whatsapp-frontdesk-mvp/TASKS.md (1–2 per chunk).
- Use BOT_MENU_YAML_PATH default ./config/bot.yaml for local config layout.
- Reverse proxy terminates TLS and forwards X-Forwarded-* headers.
- Admin may close any assigned conversation without self-assignment (responding still requires assignment).
- Admin reassign targets must be agents or the current admin (no reassignment to other admins).

## Gotchas / Risks discovered
- Required WhatsApp credentials have no defaults; ensure they are set in non-dev environments.
- Login audit events have no conversation_id; table allows NULL only for login events.

## Safe resume instructions
- Stay on impl/whatsapp-frontdesk-mvp branch.
- Start with T1.5 by implementing the YAML bot engine and EN_ESPERA auto-messages.
