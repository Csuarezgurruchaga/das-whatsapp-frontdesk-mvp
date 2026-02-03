# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-03

## Completed
- T0.1 config conventions; T0.2 bot.yaml validated; T1.1–T1.5 core data/auth/bot; T2.1 inbound webhook; T2.2 outbound send + receipts; T2.3 realtime WS events; T3.1 FrontDesk UI; T3.2 deployment hardening docs + allowlist hook

## Current / Next
- Next task: T4.1 End-to-end acceptance run + rollback notes
- Status: READY

## How to verify
- Load `/` in a browser; login; verify tabs, take, send, close, and admin reassign/assign-to-self flows.
- Open `/realtime/ws` with a valid session cookie; trigger take/reassign/close or send/receive and observe `conversation.updated` + `message.new` payloads.

## Important constraints
- BOT_MENU_YAML_PATH default ./config/bot.yaml; reverse proxy terminates TLS + forwards X-Forwarded-*
- Allowlist hook uses WHATSAPP_WEBHOOK_ALLOWLIST_* envs; enable only behind trusted proxy
- Admin close/reassign rules per SPEC; bot reload keeps last-known-good config on invalid YAML

## Gotchas / Risks discovered
- WebSocket auth depends on session cookies; WhatsApp credentials required for full send/receive

## Safe resume instructions
- Stay on impl/whatsapp-frontdesk-mvp; execute T4.1 checklist in local + staging/on-prem
