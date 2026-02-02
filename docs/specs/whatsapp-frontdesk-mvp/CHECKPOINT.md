# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-02

## Completed
- T0.1 documented config conventions (env vars + reverse proxy + webhook URL)
- T0.2 validated bot.yaml and added local config artifact

## Current / Next
- Next task: T1.1 data model for conversations/messages/read state
- Status: READY

## Important constraints
- Implement only tasks defined in docs/specs/whatsapp-frontdesk-mvp/TASKS.md (1–2 per chunk).
- Use BOT_MENU_YAML_PATH default ./config/bot.yaml for local config layout.
- Reverse proxy terminates TLS and forwards X-Forwarded-* headers.

## Gotchas / Risks discovered
- Required WhatsApp credentials have no defaults; ensure they are set in non-dev environments.

## Safe resume instructions
- Stay on impl/whatsapp-frontdesk-mvp branch.
- Start with T1.1 by defining the data model and persistence layer for conversations/messages/read state.
