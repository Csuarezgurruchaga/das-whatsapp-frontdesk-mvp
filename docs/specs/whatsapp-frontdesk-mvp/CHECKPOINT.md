# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-02-02

## Completed
- T0.1 config conventions; T0.2 bot.yaml validated; T1.1–T1.5 core data/auth/bot; T2.1 inbound webhook; T2.2 outbound send + receipts

## Current / Next
- Next task: T2.3 WebSocket realtime (messages + list updates)
- Status: READY

## How to verify
- POST `/conversations/{id}/messages` with valid auth; confirm WhatsApp send + receipt rows via webhook statuses.

## Important constraints
- BOT_MENU_YAML_PATH default ./config/bot.yaml; reverse proxy terminates TLS + forwards X-Forwarded-*
- Admin close/reassign rules per SPEC; bot reload keeps last-known-good config on invalid YAML

## Gotchas / Risks discovered
- WhatsApp credentials required; login audit events may omit conversation_id

## Safe resume instructions
- Stay on impl/whatsapp-frontdesk-mvp; implement WS events for take/reassign/close + inbound/outbound
