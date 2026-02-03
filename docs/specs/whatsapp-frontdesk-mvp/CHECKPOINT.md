# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-03

## Completed
- T0.1 config conventions; T0.2 bot.yaml validated; T1.1–T1.5 core data/auth/bot; T2.1 inbound webhook; T2.2 outbound send + receipts; T2.3 realtime WS events

## Current / Next
- Next task: T3.1 FrontDesk UI (3 tabs + 3-column layout + core actions)
- Status: READY

## How to verify
- Open `/realtime/ws` with a valid session cookie; trigger take/reassign/close or send/receive and observe `conversation.updated` + `message.new` payloads.

## Important constraints
- BOT_MENU_YAML_PATH default ./config/bot.yaml; reverse proxy terminates TLS + forwards X-Forwarded-*
- Admin close/reassign rules per SPEC; bot reload keeps last-known-good config on invalid YAML

## Gotchas / Risks discovered
- WebSocket auth depends on session cookies; WhatsApp credentials required for full send/receive

## Safe resume instructions
- Stay on impl/whatsapp-frontdesk-mvp; wire T3.1 UI to realtime updates and core APIs
