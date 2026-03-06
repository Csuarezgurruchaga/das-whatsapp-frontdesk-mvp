# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-03

## Completed
- T0.1 config conventions; T0.2 bot.yaml validated; T1.1–T1.5 core data/auth/bot; T2.1 inbound webhook; T2.2 outbound send + receipts; T2.3 realtime WS events; T3.1 FrontDesk UI; T3.2 deployment hardening docs + allowlist hook; T4.1 acceptance checklist + rollback notes

## Current / Next
- Next task: None (all tasks complete)
- Status: DONE

## How to verify
- Use the acceptance checklist in `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md` and execute in local + staging/on-prem.

## Important constraints
- BOT_MENU_YAML_PATH default ./config/bot.yaml; reverse proxy terminates TLS + forwards X-Forwarded-*
- Allowlist hook uses WHATSAPP_WEBHOOK_ALLOWLIST_* envs; enable only behind trusted proxy
- Admin close/reassign rules per SPEC; bot reload keeps last-known-good config on invalid YAML

## Gotchas / Risks discovered
- WebSocket auth depends on session cookies; WhatsApp credentials required for full send/receive.
- Acceptance run checklist is currently waived pending environment access.

## Safe resume instructions
- Stay on `dev`; run the checklist in `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md` and remove waivers when executed.
