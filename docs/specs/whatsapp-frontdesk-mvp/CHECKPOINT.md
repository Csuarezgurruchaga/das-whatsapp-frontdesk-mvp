# CHECKPOINT — whatsapp-frontdesk-mvp

Last updated: 2026-04-17

## Completed
- T0.1 config conventions; T0.2 bot.yaml validated; T1.1–T1.5 core data/auth/bot; T2.1 inbound webhook; T2.2 outbound send + receipts; T2.3 realtime WS events; T3.1 FrontDesk UI; T3.2 deployment hardening docs + allowlist hook; T4.1 acceptance checklist + rollback notes

## Current / Next
- Next task: Debian deploy execution using `Dockerfile.prod` + `docker-compose.prod.yml`
- Status: DONE (implementation) / READY_FOR_DEPLOY

## How to verify
- Core functional verification was executed in a real local prod-like setup on `2026-04-17`.
- Use the acceptance record in `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md`.
- For Debian packaging/deploy, use `DEPLOYMENT_PROD.md`.

## Important constraints
- BOT_MENU_YAML_PATH default ./config/bot.yaml; reverse proxy terminates TLS + forwards X-Forwarded-*
- Allowlist hook uses WHATSAPP_WEBHOOK_ALLOWLIST_* envs; enable only behind trusted proxy
- Admin close/reassign rules per SPEC; bot reload keeps last-known-good config on invalid YAML

## Gotchas / Risks discovered
- WebSocket auth depends on session cookies; WhatsApp credentials required for full send/receive.
- Local prod-like runs with real WhatsApp credentials are operationally risky if the stack points at a live WABA; keep local-safe and prod-like modes explicitly separated.
- Remaining unobserved audit items from the latest acceptance run: `MESSAGE_SENT_FAILED`, and receipt statuses `read` / `failed`.
- The blocked-handoff path outside configured business hours was not re-executed in the latest real run.

## Safe resume instructions
- Stay on `dev`.
- For local development, use `docker-compose.local.yml` + `.env.staging.local.example`.
- For server deployment, use `Dockerfile.prod`, `docker-compose.prod.yml`, `nginx.prod.conf`, and `DEPLOYMENT_PROD.md`.
- If a future session needs another real WhatsApp acceptance run, back up and restore dispatcher routing explicitly before and after the test window.
