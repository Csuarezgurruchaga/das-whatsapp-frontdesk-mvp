# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-02

## Completed
- T0.1 documented config conventions (env vars + reverse proxy + webhook URL)
- T0.2 validated bot.yaml and added local config artifact
- T1.1 core data model + Alembic baseline migration + CRUD access layer
- T1.2 audit events + message receipts tables and CRUD helpers
- T1.3 session auth (login/logout) + authorization guards + sessions table
- T1.4 handoff state transitions (take/reassign/close) + audit events
- T1.5 YAML bot loader/validator + routing + admin reload endpoint + EN_ESPERA auto-replies
- T2.1 WhatsApp inbound webhook (verify + signature + idempotency) + inbound routing + receipt persistence (flush bot history for batched payloads)

## Current / Next
- Next task: T2.2 WhatsApp outbound send (text) + receipt lifecycle
- Status: READY

## How to verify
- Send GET ` /webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=123` with `WHATSAPP_VERIFY_TOKEN` set; expect `123`.
- POST a WhatsApp webhook payload with a valid signature; expect 200 and inbound messages persisted (dedupe by `whatsapp_message_id`).
- POST the same payload again; expect no duplicate inbound messages.

## Important constraints
- Implement only tasks defined in docs/specs/whatsapp-frontdesk-mvp/TASKS.md (1–2 per chunk).
- Use BOT_MENU_YAML_PATH default ./config/bot.yaml for local config layout.
- Reverse proxy terminates TLS and forwards X-Forwarded-* headers.
- Admin may close any assigned conversation without self-assignment (responding still requires assignment).
- Admin reassign targets must be agents or the current admin (no reassignment to other admins).

## Gotchas / Risks discovered
- Required WhatsApp credentials have no defaults; ensure they are set in non-dev environments.
- Login audit events have no conversation_id; table allows NULL only for login events.
- Bot menu reload keeps last-known-good config; invalid YAML returns errors without swapping config.

## Safe resume instructions
- Stay on impl/whatsapp-frontdesk-mvp branch.
- Continue with T2.2 by implementing WhatsApp outbound send (text) and receipt lifecycle persistence.
