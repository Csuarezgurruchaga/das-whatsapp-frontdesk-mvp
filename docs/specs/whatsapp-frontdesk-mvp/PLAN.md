# PLAN — WhatsApp FrontDesk Core MVP

## Milestone 0 — Inputs & scope lock
- Confirm Spec A scope boundaries vs Spec B.
- Obtain initial `bot.yaml` content (menus + approved copy) as an input artifact.
- Define rollout environments (local via `docker-compose`, on-prem via reverse proxy + TLS).

## Milestone 1 — Data model + core invariants
- Define the conversation state machine and invariants:
  - exclusivity (only one `assigned_to`),
  - atomic “take conversation” semantics,
  - force-reassign semantics,
  - close semantics and post-close new conversation linking (`previous_conversation_id`).
- Implement persistence for:
  - conversations, messages, per-user read state,
  - critical conversation events (audit),
  - WhatsApp receipts/events (audit-only).

## Milestone 2 — WhatsApp integration (inbound/outbound)
- Implement inbound webhook:
  - Meta verification handshake,
  - signature verification,
  - optional IP allowlist at reverse proxy (environment-controlled),
  - idempotent ingestion (dedupe by `whatsapp_message_id`).
- Implement outbound send for text messages.
- Persist outbound send attempts and receipt lifecycle for audit.

## Milestone 3 — Bot engine (YAML-driven)
- Implement YAML loading/validation using the decided schema (`root` + `nodes`).
- Implement runtime reload endpoint (admin-only), rejecting invalid YAML while keeping last-known-good config.
- Implement the bot router for `CHATBOT` state:
  - numeric option handling,
  - global invalid input response,
  - support submenus and terminal texts,
  - handoff as an explicit menu option (`action: "handoff"`) gated by business hours/holidays (blocked handoff stays in `CHATBOT` with an informational reply).
- Implement `EN_ESPERA` behavior:
  - entry auto-reply (fixed text),
  - single-shot follow-up on first inbound message while waiting.

## Milestone 4 — FrontDesk app (main attention screen)
- Authentication:
  - session-based login/logout,
  - role-based authorization (`agent`, `admin`).
- Main screen layout:
  - 3 columns (list / chat / details),
  - 3 tabs: `CHATBOT`, `EN ESPERA`, `ASIGNADOS`.
- Operations:
  - preview in `CHATBOT` and `EN ESPERA`,
  - take conversation (atomic),
  - assigned chat send/receive text,
  - canned responses (3),
  - close conversation (audited),
  - admin reassign and admin “assign to self” for responding.

## Milestone 5 — Realtime + UX consistency
- WebSocket contract for:
  - conversation list updates by tab,
  - message stream updates for open conversation.
- Ensure consistent unread and last-activity updates across:
  - agent view,
  - admin view (separate read markers).

## Milestone 6 — Observability, hardening, and release
- Structured logs correlated by `conversation_id`.
- Minimal operational dashboards/queries (counts by state, recent failures) if needed.
- Local runbook and on-prem deployment notes:
  - reverse proxy headers,
  - webhook URL and tokens,
  - session cookie settings.
- Rollback strategy:
  - safe re-deploy,
  - disable bot YAML reload endpoint if needed,
  - fall back to signature-only if allowlist is misconfigured.

## Test strategy (high-level)
- Unit tests: YAML validation, bot routing, state transitions, idempotent webhook ingestion.
- Integration tests: atomic take/reassign, outbound send error handling, receipt persistence.
- Browser smoke: FrontDesk loads, can log in, can take a conversation, can send/receive messages (happy path).
