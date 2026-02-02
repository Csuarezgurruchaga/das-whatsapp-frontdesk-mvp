# SPEC — WhatsApp Chatbot + FrontDesk (Core MVP)

## Summary
Build an on‑premise compatible system that integrates with the WhatsApp Business Cloud API to:
- run a rule-based WhatsApp chatbot (numeric menu),
- support configurable bot sub-menus/flows loaded from YAML,
- support human handoff with queue + exclusive assignment,
- provide a FrontDesk web UI (main attention screen) with 3 tabs and chat handling,
- provide minimal canned responses in the UI,
- allow an operator to close a conversation (minimal action; tipification not mandatory for closing),
- allow admin to reassign an assigned conversation to another agent.

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

## Goals / Non-goals
### Goals (Spec A / Core)
- WhatsApp inbound webhook ingestion and persistence of message history (user + bot + agent).
- Chatbot menu + sub-menus/flows loaded from a YAML file; option 6 triggers handoff to humans (and some flows may also offer handoff at the end).
- Conversation state machine: `CHATBOT` → `EN_ESPERA` → `ASIGNADO` → `CERRADO`.
- FrontDesk main screen:
  - login (agent/admin),
  - three tabs: `CHATBOT`, `EN ESPERA`, `ASIGNADOS`,
  - preview conversations in `CHATBOT` and `EN ESPERA`,
  - atomic “take conversation” from `EN ESPERA`,
  - chat send/receive text for assigned conversations,
  - canned responses (3 buttons): `Mensaje inicial`, `Mensaje de cierre`, `Mensaje sin respuesta`,
  - close conversation action (audited), removing it from all 3 tabs.
- Admin can reassign an `ASIGNADO` conversation to another agent.
- Minimal observability: structured logs correlated by `conversation_id`.

### Non-goals (in Spec A)
- Generative AI / LLM responses.
- Omnichannel.
- Multi-tenant “full” support.
- Additional screens (dashboards, reports, advanced settings).

### Potential goals for Spec B (Extras) — pending confirmation
- Attachments (upload, store, send via WhatsApp, render in UI).
- Tipification (tags/categories).
- Realtime fallback modes (polling/SSE fallback) and hardening.

## Constraints
- Production deployment must be on-premise (no mandatory managed cloud dependencies).
- Initial testing should work locally, preferably via `docker-compose`.
- Realtime choice: WebSockets (primary) for message/list updates (no typing/presence in MVP).
- Authentication choice: server-side sessions with secure cookies.
- Backend: Python 3.11+ with FastAPI.
- Database: MySQL (dedicated database `chatbot_mvp` with a dedicated, least-privileged user).
- Persistence: SQLAlchemy 2.0 ORM + Alembic migrations (versioned).
- DB driver: PyMySQL (default), with the option to migrate to `mysqlclient` if required.
- WhatsApp integration: WhatsApp Business Cloud API (webhook inbound + outbound send).
- Bot menus/flows must be configurable via YAML stored on disk; YAML path is configured via environment/config and reload is triggered via an admin-only endpoint (no UI required).
  - Env var: `BOT_MENU_YAML_PATH` (default `./config/bot.yaml`).

## Configuration conventions
### Config artifact layout
- Runtime config artifacts live under `./config/` at repo root.
- Default bot menu YAML: `./config/bot.yaml` (override via `BOT_MENU_YAML_PATH`).

### Environment variables (initial)
- `APP_ENV`: `development` | `staging` | `production` (default: `development`).
- `BOT_MENU_YAML_PATH`: path to bot YAML (default: `./config/bot.yaml`).
- `SESSION_SECRET`: session signing secret (required; no default).
- `WHATSAPP_VERIFY_TOKEN`: webhook verification token (required; no default).
- `WHATSAPP_APP_SECRET`: app secret for signature validation (required; no default).
- `WHATSAPP_ACCESS_TOKEN`: Cloud API access token (required; no default).
- `WHATSAPP_PHONE_NUMBER_ID`: Cloud API phone number id for outbound sends (required; no default).

### Reverse proxy + webhook URL conventions
- Public webhook URL: `https://<public-host>/webhooks/whatsapp` (GET verification, POST events).
- Reverse proxy terminates TLS and forwards `X-Forwarded-Proto`, `X-Forwarded-For`, `X-Forwarded-Host` (and optionally `X-Forwarded-Port`).
- If IP allowlist is used, apply it at the reverse proxy layer; app still relies on signature verification in non-dev environments.

## Key Flows
1) **Inbound message processing (WhatsApp → backend)**
   - Verify webhook (Meta verification handshake).
   - Persist inbound messages and update the conversation “last activity” + unread counters.
   - Route handling by conversation state:
     - `CHATBOT`: bot replies (menu + validation; option 6 triggers handoff).
     - `EN_ESPERA`: append inbound messages to history; bot sends no replies except:
       - exactly one entry auto-reply when transitioning into `EN_ESPERA`, and
       - at most one additional follow-up auto-reply on the first inbound message received while waiting (single-shot).
     - `ASIGNADO`: message is appended and shown to assigned agent in UI.
     - `CERRADO`: create a new conversation (per decision) and start in `CHATBOT` with the menu.

2) **Handoff + assignment (queue → exclusive owner)**
   - User chooses option 6: conversation moves to `EN_ESPERA`.
   - Agents/admin can preview `EN ESPERA` items.
   - Agent clicks “TOMAR CONVERSACIÓN”: operation must be atomic; only one agent can succeed.
   - On success: `assigned_to=<agent_id>`, state becomes `ASIGNADO`, it disappears from others’ `EN ESPERA` and appears in the taker’s `ASIGNADOS`.

3) **Agent handling + close (FrontDesk → WhatsApp)**
   - Agent sends text messages from the `ASIGNADOS` tab; messages are delivered to user via WhatsApp.
   - User replies; UI receives updates and renders inbound messages.
   - Agent/admin closes conversation: state becomes `CERRADO`, audit “who/when”; conversation disappears from all three tabs.
   - Admin can reassign a conversation to a different agent; it should disappear from the previous agent’s `ASIGNADOS` and appear in the new agent’s `ASIGNADOS`.

## Data / Interfaces
### Bot YAML configuration (high-level)
The bot menu tree is defined in a YAML file. At minimum, nodes support:
- enter text (`on_enter_text`),
- an optional terminal/final text (`terminal_text`),
- options that either route to another node (`next`) or trigger an action (e.g., `handoff`).

Handoff is represented as an explicit option in a menu (not an automatic terminal action).

#### YAML schema (decided)
- Top-level:
  - `root`: node id (string)
  - `invalid_input_text`: string shown when the user replies with an unknown option key
  - `timezone`: IANA timezone used to interpret schedule-based rules (default: `America/Argentina/Buenos_Aires`)
  - `handoff_schedule`: optional object used to gate `action: "handoff"`:
    - `windows`: list of `{ days: [mon..sun], start: "HH:MM", end: "HH:MM" }`
    - `closed_dates`: optional list of `YYYY-MM-DD`
    - `closed_ranges`: optional list of `{ start: "YYYY-MM-DD", end: "YYYY-MM-DD" }` (end inclusive)
  - `nodes`: map of node id → node definition
- Node:
  - `on_enter_text`: string
  - `terminal_text`: optional string
  - `options`: list of:
    - `key`: numeric string (e.g., `"1"`, `"2"`, …)
    - `label`: string
    - either `next: <node_id>` or `action: "handoff"`

### Core entities (conceptual)
- **User**: `id`, `username`, `password_hash`, `role` (`agent` | `admin`), `created_at`, `disabled_at?`.
- **Contact**: `id`, `whatsapp_number`, `display_name?`, `created_at`.
- **Conversation**:
  - `id`, `contact_id`, `state` (`CHATBOT` | `EN_ESPERA` | `ASIGNADO` | `CERRADO`),
  - `assigned_to?`, `created_at`, `updated_at`, `last_activity_at`,
  - `closed_at?`, `closed_by?`.
  - `previous_conversation_id?` (set when creating a new conversation after `CERRADO`).
- **Message**:
  - `id`, `conversation_id`, `direction` (`INBOUND` | `OUTBOUND`),
  - `sender_type` (`USER` | `BOT` | `AGENT`),
  - `text?`, `created_at`,
  - `whatsapp_message_id?` (for traceability).
- **MessageReceipt** (audit-only):
  - `id`, `message_id` (or `whatsapp_message_id`), `status` (`sent` | `delivered` | `read` | `failed`), `payload_raw?`, `created_at`.
- **ConversationEvent** (critical audit events):
  - `id`, `conversation_id`, `type` (`TAKEN` | `REASSIGNED` | `CLOSED` | `MESSAGE_SENT_FAILED` | `LOGIN_SUCCESS` | `LOGIN_FAIL`),
  - `actor_user_id?`, `meta_json?`, `created_at`.
- **ConversationReadState** (or equivalent): per-user last seen marker/unread count model (MVP: mark conversation as “read” when the user opens it).

### External interfaces
- **WhatsApp webhook (inbound)**: receives user messages and delivery events/receipts (audit-only persistence for `sent`, `delivered`, `read`, `failed`).
- **WhatsApp outbound send**: send text messages to a WhatsApp number (Cloud API).
- **FrontDesk API**:
  - auth: login/logout, session management,
  - list conversations by tab,
  - get conversation history,
  - take conversation (atomic),
  - send message,
  - close conversation,
  - reassign conversation (admin-only).
- **Realtime**:
  - WebSocket channel for conversation list updates and message stream.

## Edge cases & Failure modes
- Two agents attempt to take the same `EN_ESPERA` conversation simultaneously: only one succeeds; other receives deterministic “already taken”.
- Duplicate webhook deliveries / retries: must be idempotent (dedupe by WhatsApp message id if available).
- Message ordering: handle out-of-order inbound events gracefully (append by timestamp and keep raw ordering metadata).
- While `EN_ESPERA`: user may send additional messages:
  - they must be persisted and visible to whoever takes it,
  - bot sends at most one additional reassurance message (single-shot); trigger: the first inbound message received while waiting.
- While `ASIGNADO`: bot should not respond (expected), but must still store the message and notify the assigned agent.
- Close action race: closing while messages arrive; close must be consistent and auditable.
- Reassign action race: reassign while agent is viewing/sending; state must remain consistent (reassignment is a force takeover).
- YAML reload failure: invalid YAML must not break the running system; reject with validation errors and keep last-known-good config.

## Observability
- Structured logs with at least: `conversation_id`, `contact_id`, `state`, `event_type`, `request_id` (if available).
- Audit trail for: take conversation, reassign (if in scope), close conversation, login attempts.
- Minimal metrics (optional): counts by state, takes per agent, message send failures (optional for MVP).

## Security / Privacy
- Authentication via secure server-side sessions (cookie attributes: `HttpOnly`, `Secure`, `SameSite` per environment).
- Authorization:
  - `agent` can only read/respond to conversations assigned to them; can preview `CHATBOT` and `EN ESPERA` as read-only.
  - `admin` can view everything and can respond only after assigning the conversation to themselves.
- Password hashing using a modern algorithm (exact choice to be decided in implementation; acceptable to defer).
- PII handling: WhatsApp numbers are sensitive; define retention/audit requirements (deferred; document operational policy separately).

## Open Questions
None.

## Deferred (explicit, non-blocking)
1) **Initial bot YAML content (copy + full menu tree)** — owner: product/ops
   - Consequence of deferring: implementation can proceed with parsing/validation + example config, but “production-ready bot copy” is blocked until YAML is delivered.
   - Default if not decided: include an example `bot.yaml` with placeholder copy for non-handoff flows.
2) **Webhook IP allowlist values (if enabled in prod)** — owner: ops/security
   - Consequence of deferring: deployments may run with signature validation only.
   - Default if not decided: allowlist disabled by default; enable via environment configuration when CIDRs are known.
3) **Reassign UX (previous agent view)** — owner: product
   - Consequence of deferring: UI behavior needs a default to avoid confusion.
   - Default if not decided: conversation is removed from the previous agent’s list; if currently open, switch to read-only with a “reassigned” notice and disable the input.

## Decision Log
- 2026-01-29 — **Decision:** Use spec slug `whatsapp-frontdesk-mvp` for Core.
  - **Rationale:** matches requested naming; keeps scope tied to MVP.
- 2026-01-29 — **Decision:** Split into Core vs Extras specs.
  - **Rationale:** reduces risk and keeps Spec A under guardrails; allows phased delivery.
  - **Risks / mitigations:** scope drift → enforce explicit scope boundary in both specs.
- 2026-01-29 — **Decision:** Include “Cerrar conversación” in Core as a minimal action; tipification not mandatory for closing.
  - **Rationale:** closing is basic operational workflow; mandatory tipification adds friction/complexity.
- 2026-01-29 — **Decision:** Spec A includes canned responses; tipification is deferred to Spec B.
  - **Rationale:** canned responses are low-risk UX acceleration; tipification adds data/config complexity.
- 2026-01-29 — **Decision:** Spec A includes admin re-assignment of assigned conversations.
  - **Rationale:** operational necessity (supervision/turns); can be implemented without attachments/tipification.
- 2026-01-29 — **Decision:** Deploy via Docker + `docker-compose` for local/dev (and on-prem compatible).
  - **Rationale:** portable and repeatable in on-prem environments.
- 2026-01-29 — **Decision:** Realtime via WebSockets.
  - **Rationale:** best fit for chat latency/UX requirements.
- 2026-01-29 — **Decision:** Auth via server-side sessions + cookies.
  - **Rationale:** simpler on-prem security posture; avoids token leakage in browser storage.
- 2026-01-29 — **Decision:** If user messages after `CERRADO`, create a new conversation.
  - **Rationale:** clean audit trail and avoids mixing resolved threads.
- 2026-01-29 — **Decision:** Chatbot flows support sub-menus and are loaded from YAML configuration.
  - **Rationale:** enables non-code iteration of menu trees and end-of-flow handoff prompts.
- 2026-01-29 — **Decision:** Bot sends an auto-reply only when entering `EN_ESPERA`.
  - **Rationale:** confirms the user is queued without spamming.
- 2026-01-29 — **Decision:** Unread/read state is tracked per agent.
  - **Rationale:** agents and admins may view different subsets; per-user read markers avoid confusion.
- 2026-01-29 — **Decision:** “Última actividad” is displayed as a relative timestamp (e.g., “hace 5 min”).
  - **Rationale:** improves scanning and prioritization in active operations.
- 2026-01-29 — **Decision:** Validate WhatsApp webhooks using verify token + signature validation.
  - **Rationale:** minimum credible security for an internet-exposed webhook.
- 2026-01-29 — **Decision:** YAML config reload via admin-only endpoint (no UI).
  - **Rationale:** safe operational control without needing app restarts or filesystem watchers.
- 2026-01-29 — **Decision:** Mark conversation as “read” when an agent opens it.
  - **Rationale:** simplest MVP behavior aligned with per-agent read state.
- 2026-01-29 — **Decision:** Admin may respond only after assigning the conversation to themselves.
  - **Rationale:** avoids double-operator collisions; keeps single-owner semantics.
- 2026-01-29 — **Decision:** Reassignment is a force takeover (immediate ownership change).
  - **Rationale:** supports real operations (turn changes/escalations) with clear authority.
- 2026-01-29 — **Decision:** Auto-reply is sent once when entering `EN_ESPERA` (fixed text defined).
  - **Rationale:** confirms queue entry while minimizing noise.
- 2026-01-29 — **Decision:** WebSockets exclude typing/presence in MVP.
  - **Rationale:** user deferred typing/presence; keep realtime scope minimal.
- 2026-01-29 — **Decision:** In YAML flows, handoff is represented as an explicit menu option (not an automatic terminal action).
  - **Rationale:** aligns with “offer handoff at the end of some flows” while keeping the user in control.
- 2026-01-29 — **Decision:** YAML lives on disk and is configured by path from environment/config.
  - **Rationale:** fits on-prem operation patterns and allows editing without rebuilding images.
- 2026-01-29 — **Decision:** YAML nodes include `on_enter_text` and `terminal_text` (plus options routing/actions).
## Changelog
- 2026-02-02 — Added backend stack decisions (FastAPI + SQLAlchemy + Alembic) and MySQL constraints.
  - reason: required to implement data model and migrations for Phase 1.
  - impact: SPEC constraints updated; no TASKS/ACCEPTANCE changes.
  - **Rationale:** supports multi-step submenus and end-of-flow copy without code changes.
- 2026-01-29 — **Decision:** Persist WhatsApp receipts/events for audit only (no UI in MVP).
  - **Rationale:** preserves delivery traceability without expanding the UI scope.
- 2026-01-29 — **Decision:** Audit is “mixed”: store last state fields plus critical event records.
  - **Rationale:** balances operational queries (current state) with forensic audit needs.
- 2026-01-29 — **Decision:** Expose webhook publicly behind a TLS reverse proxy.
  - **Rationale:** standard on-prem pattern for internet-facing webhooks.
- 2026-01-29 — **Decision:** Business timezone is fixed for relative time display (`America/Argentina/Buenos_Aires`).
  - **Rationale:** consistent operations for a single-business locale.
- 2026-01-29 — **Decision:** Auto-reply text on entering `EN_ESPERA` is: “Te estoy derivando con un agente 🙌 En breve te responderá”.
  - **Rationale:** user-provided copy.
- 2026-01-29 — **Decision:** Business timezone identifier is `America/Argentina/Buenos_Aires`.
  - **Rationale:** user-selected fixed business timezone.
- 2026-01-29 — **Decision:** YAML path env var is `BOT_MENU_YAML_PATH` with default `./config/bot.yaml`.
  - **Rationale:** good dev ergonomics while remaining configurable for on-prem.
- 2026-01-29 — **Decision:** While `EN_ESPERA`, after the initial entry auto-reply, send at most one additional “still waiting” message (single-shot, not periodic).
  - **Rationale:** provides reassurance without spamming; avoids time-based scheduling complexity.
- 2026-01-29 — **Decision:** Persist WhatsApp message lifecycle receipts for audit: `sent`, `delivered`, `read`, and `failed`.
  - **Rationale:** complete traceability of outbound delivery without UI scope increase.
- 2026-01-29 — **Decision:** Audit events (mixed model) include: `TAKEN`, `REASSIGNED`, `CLOSED`, plus `MESSAGE_SENT_FAILED`, plus `LOGIN_SUCCESS`/`LOGIN_FAIL`.
  - **Rationale:** balances operational troubleshooting and security/compliance needs on-prem.
- 2026-01-29 — **Decision:** Typing/presence is deferred (not implemented) in the Core MVP.
  - **Rationale:** reduces realtime surface area while shipping core chat flow.
- 2026-01-29 — **Decision:** Store timestamps in UTC and compute relative time in the frontend using business timezone `America/Argentina/Buenos_Aires`.
  - **Rationale:** standard web approach; consistent storage with correct business-local display.
- 2026-01-29 — **Decision:** While `EN_ESPERA`, send the one additional reassurance message on the first inbound message received while waiting (single-shot).
  - **Rationale:** avoids timers while still reassuring users who keep writing.
- 2026-01-29 — **Decision:** YAML handoff option uses `action: "handoff"`.
  - **Rationale:** readable and extensible enough for MVP.
- 2026-01-29 — **Decision:** Invalid input handling is global: if the option key is not found, re-show the same menu with a standard message.
  - **Rationale:** simplest consistent UX for a menu tree.
- 2026-01-29 — **Decision:** Deduplicate inbound messages using `whatsapp_message_id` as a unique key.
  - **Rationale:** most reliable idempotency anchor provided by WhatsApp.
- 2026-01-29 — **Decision:** Bot YAML schema uses `root` + `nodes` mapping and a global `invalid_input_text`.
  - **Rationale:** simplest structure to validate and reference while keeping YAML editable.
- 2026-01-29 — **Decision:** Option keys in YAML are numeric-only (strings).
  - **Rationale:** aligns with WhatsApp numeric menu UX and reduces parsing ambiguity.
- 2026-01-29 — **Decision:** Bot YAML content (real copy) will be provided as an input artifact (not generated by the system).
  - **Rationale:** copy typically requires business/legal approval; keeping it external avoids code changes.
- 2026-01-29 — **Decision:** EN_ESPERA follow-up message is distinct from the entry auto-reply.
  - **Rationale:** clearer UX; avoids repeating the same message verbatim.
- 2026-01-30 — **Decision:** EN_ESPERA follow-up (single-shot) message text is: “Seguimos con tu caso. En breve un agente te responde. Gracias por tu paciencia 🙌”.
  - **Rationale:** acknowledges the user’s persistence without spamming; copy is short and operational.
- 2026-01-30 — **Decision:** While `EN_ESPERA`, send the follow-up message exactly once on the first inbound message received while waiting; after that, inbound messages are persisted but do not trigger any additional bot replies.
  - **Rationale:** avoids timers/schedulers while still reassuring once; preserves history for the agent who takes it.
- 2026-01-30 — **Decision:** Handoff availability is gated by business hours + holidays configured in bot YAML (`handoff_schedule`) using timezone `America/Argentina/Buenos_Aires`.
  - **Rationale:** allows ops to adjust schedule without code changes while keeping user-controlled handoff.
- 2026-01-30 — **Decision:** When handoff is blocked (outside schedule / holiday), the conversation stays in `CHATBOT` and the bot replies with an “operators available 9–18” message (copy as defined below).
  - **Rationale:** prevents queue spam outside business hours and provides a clear operational expectation to the user.
- 2026-01-30 — **Decision:** Default `handoff_schedule.windows` is Mon–Fri 09:00–18:00 and `closed_ranges.end` is inclusive.
  - **Rationale:** matches the existing DAS bot behavior and keeps schedule semantics unambiguous.
- 2026-01-30 — **Decision:** Blocked-handoff reply text is:
  - “Nuestros/as operadores/as se encuentran disponibles los días hábiles de 9 a 18hs. Si se encuentra fuera de este rango horario puede comunicarse vía mail a través de contacto@das.gob.ar.
Por emergencias comunicarse al 0810-999-767-3876
 
Saludos”
  - **Rationale:** reuse the existing approved copy from the prior DAS decision-tree YAML.
- 2026-01-30 — **Decision:** When handoff is blocked, the bot re-shows the current menu after sending the blocked-handoff reply; if the user selects handoff again while blocked, the bot repeats the message every time.
  - **Rationale:** consistent WhatsApp numeric-menu UX; clear feedback on repeated attempts.
- 2026-01-29 — **Decision:** New conversations created after `CERRADO` link to the previous via `previous_conversation_id`.
  - **Rationale:** improves audit/navigation while keeping conversations separate.
- 2026-01-29 — **Decision:** Webhook IP allowlist is optional by environment (in addition to signature validation).
  - **Rationale:** enables defense-in-depth when ops can maintain CIDRs without making it mandatory.
- 2026-01-29 — **Decision:** Admin has its own read state (per-user read markers).
  - **Rationale:** admins can review without affecting agents’ unread indicators.

## Changelog
- 2026-01-29 — Initial SPEC created from `PRD.md` + interview Round 1 answers.
  - reason: establish a spec-anchored contract before implementation
  - impact: requires follow-up interview rounds to close Open Questions before PLAN/TASKS/ACCEPTANCE
- 2026-01-29 — Updated realtime scope to exclude typing/presence.
  - reason: user deferred typing/presence in Round 6 (Q39=D)
  - impact: WebSocket contract limited to message/list updates; acceptance and tasks must reflect
- 2026-01-30 — Resolved EN_ESPERA follow-up copy + trigger semantics.
  - reason: product copy and behavior clarified (single-shot follow-up; later messages do not trigger bot replies)
  - impact: Open Questions emptied; acceptance/spec updated for EN_ESPERA follow-up behavior

## Glossary
- **WhatsApp Business Cloud API:** Meta-hosted API to receive/send WhatsApp messages via webhooks and REST endpoints.
- **Handoff:** transition from bot automation to human handling.
- **FrontDesk:** web UI used by agents/admins to manage and reply to conversations.
- **EN_ESPERA:** queued state awaiting an agent to take the conversation.
- **ASIGNADO:** state where exactly one agent exclusively owns the conversation.
- **Force takeover:** admin reassigns immediately, replacing the prior assigned agent.
