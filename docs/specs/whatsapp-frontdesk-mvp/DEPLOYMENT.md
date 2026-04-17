# DEPLOYMENT — WhatsApp FrontDesk Core MVP

## Acceptance run checklist

Last updated: 2026-04-17

### Scope
- Validate ACCEPTANCE.md criteria A0–A7.
- Execute in both local and staging/on-prem environments.

### Prereqs
- App is running and DB is migrated.
- At least two agent accounts and one admin account exist.
- WhatsApp credentials are configured and the public webhook is reachable.
- `BOT_MENU_YAML_PATH` points to the approved `bot.yaml`.

### Execution record
- Local prod-like: PARTIAL PASS on `2026-04-17`
- Staging/on-prem: PENDING

### Local prod-like execution summary (`2026-04-17`)
- Runtime:
  - Docker + MySQL 8 + Nginx
  - `APP_ENV=staging`
  - HTTPS via `ngrok`
  - signed webhook validation enabled
- Real WhatsApp path:
  - temporary dispatcher cutover to DAS local
  - real inbound from test handset
  - real bot replies from DAS
  - dispatcher restored after the run
- Proven in this run:
  - A0 browser smoke
  - A1 YAML routing + invalid input
  - A2 entry to `EN_ESPERA` + one-shot waiting follow-up
  - A3 atomic take
  - A4 agent send/receive
  - A5 admin reassign + reply safety
  - A6 close + new conversation after close
  - A7 invalid signature rejection + duplicate delivery idempotency
- Observed audit/receipts in DB:
  - `TAKEN`, `REASSIGNED`, `CLOSED`, `LOGIN_SUCCESS`, `LOGIN_FAIL`
  - receipt statuses `sent`, `delivered`
- Still not explicitly observed in that run:
  - blocked handoff outside business hours
  - `MESSAGE_SENT_FAILED`
  - receipt statuses `read`, `failed`

### Checklist template (run per environment)
#### A0 - Browser smoke (web)
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Open `/` in Chromium.
  - Confirm no critical console errors.
  - Complete the primary happy-path flow end-to-end.

#### A1 - Bot YAML-driven menu (with submenus)
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Validate YAML schema (optional automation): `python scripts/validate_bot_yaml.py --path config/bot.yaml`.
  - Send numeric replies and confirm menu routing.
  - Confirm invalid input triggers the global invalid-input response and re-shows the menu.
  - Confirm handoff is offered via `action: "handoff"` where configured.

#### A2 - Handoff to queue (EN_ESPERA)
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - During business hours, select handoff and confirm transition to `EN_ESPERA`.
  - Outside hours/holiday, confirm the blocked-handoff reply matches ACCEPTANCE.md A2 and the menu is re-shown.
  - On entering `EN_ESPERA`, confirm the entry auto-reply is sent once.
  - While waiting, send a first inbound message and confirm the single-shot follow-up reply.
  - Send additional inbound messages and confirm no further bot replies.

#### A3 - Exclusive "take conversation" (atomic)
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Open `EN ESPERA` in two agent sessions.
  - Attempt to take the same conversation concurrently; confirm only one succeeds.
  - Confirm it disappears from other agents' `EN ESPERA` and appears only in the taker's `ASIGNADOS`.

#### A4 - Assigned chat send/receive (text)
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Send a message from `ASIGNADOS`; confirm user receives it via WhatsApp.
  - Reply from WhatsApp; confirm the message appears in the assigned agent UI.

#### A5 - Admin reassign + admin reply safety
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Reassign an assigned conversation to another agent or to self (not to other admins).
  - Confirm it moves between `ASIGNADOS` accordingly.
  - Confirm admin can reply only after assigning the conversation to themselves.

#### A6 - Close conversation + post-close new conversation linking
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Close a conversation; confirm state `CERRADO`, audit fields set, and it disappears from all tabs.
  - As admin, close an assigned conversation without self-assignment.
  - Send a new user message after close; confirm a new conversation in `CHATBOT` linked via `previous_conversation_id`.

#### A7 - Security + audit baseline
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Confirm invalid webhook signatures are rejected in non-dev environments.
  - Replay a duplicate webhook delivery; confirm no duplicate inbound message is created.
  - Confirm audit events are persisted in `conversation_events` for: TAKEN, REASSIGNED, CLOSED, MESSAGE_SENT_FAILED, LOGIN_SUCCESS, LOGIN_FAIL.
  - Confirm WhatsApp receipts are persisted in `message_receipts` (sent/delivered/read/failed).

### Waiver / residual log
- 2026-02-03 — original checklist was waived due missing runtime/credentials.
- 2026-04-17 — waiver replaced by a real local prod-like execution record.
- 2026-04-17 — residual gaps kept explicit: blocked-handoff outside schedule, `MESSAGE_SENT_FAILED`, and receipt statuses `read` / `failed` were not forced during the run.

### Rollback procedure
1) Identify the last known good release (image tag or commit) and corresponding DB snapshot (if available).
2) Redeploy the previous image/version using your standard deployment method.
3) If the bot reload endpoint needs to be disabled, block `POST /bot/reload` at the reverse proxy or temporarily disable admin accounts.
4) Verify the app loads and core read-only access works (login + tab lists).

## Reverse proxy requirements
- Terminate TLS at the reverse proxy and forward traffic to the app over HTTP.
- Forward the original request headers:
  - `X-Forwarded-Proto`, `X-Forwarded-For`, `X-Forwarded-Host` (and optionally `X-Forwarded-Port`).
- Preserve the Host header for URL construction and callbacks.
- Support WebSocket upgrades on `/realtime/ws` (set `Upgrade` + `Connection` headers).
- Route `/webhooks/whatsapp` and `/` to the app service.

## Optional webhook allowlist (recommended at proxy)
- Allowlist should be enforced at the reverse proxy when required by ops/security.
- The app also supports an optional allowlist hook (disabled by default):
  - `WHATSAPP_WEBHOOK_ALLOWLIST_ENABLED` = `true` to enable.
  - `WHATSAPP_WEBHOOK_ALLOWLIST_CIDRS` = comma-separated CIDRs (e.g. `203.0.113.0/24,198.51.100.4/32`).
- When enabled, the app reads the left-most IP from `X-Forwarded-For` (or falls back to the direct client IP).
- Ensure the proxy strips any client-supplied `X-Forwarded-For` and sets its own value.

## Session cookie settings
- `APP_ENV=development` → cookies are not `Secure` (local HTTP is allowed).
- `APP_ENV=staging|production` → cookies are `Secure`, `HttpOnly`, `SameSite=Lax` (requires TLS).
- Keep `SESSION_SECRET` set in all non-dev environments.

## Config validation
- On startup, in `staging`/`production`, the app validates required env vars:
  - `DATABASE_URL`, `SESSION_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`,
    `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`.
- If allowlist is enabled, CIDRs are validated at startup; invalid or empty values fail fast.
