# TASKS

## Phase 0 — Setup / scaffolding
- T0.1 Spec artifacts & repo conventions
  - Goal: Ensure repo has a clear MVP structure and configuration conventions for on-prem/local usage.
  - Inputs: `docs/specs/whatsapp-frontdesk-mvp/SPEC.md`, `docs/specs/whatsapp-frontdesk-mvp/PLAN.md`.
  - Outputs: Documented env vars/config keys; agreed folder layout for config artifacts (e.g., `./config/bot.yaml`).
  - Steps:
    - Define environment variables and their defaults (including `BOT_MENU_YAML_PATH`).
    - Define reverse proxy assumptions (headers, TLS termination) and webhook URL conventions.
  - Done condition: Config conventions are documented and referenced by later tasks.
  - Depends on: []
  - Risks: Misaligned config conventions cause later rework.
  - Test/Verification: Manual review of docs and env var list.

- T0.2 Collect initial `bot.yaml` (approved copy)
  - Goal: Obtain the initial YAML menu tree with approved copy to run the bot end-to-end.
  - Inputs: Stakeholder-provided YAML content; decided schema in `SPEC.md`.
  - Outputs: A validated `bot.yaml` instance (content artifact) ready for deployment.
  - Steps:
    - Request the complete YAML file from product/ops.
    - Validate it against the schema (root/nodes/options, numeric keys).
  - Done condition: YAML validates and includes required menus/submenus and handoff options.
  - Depends on: [T0.1]
  - Risks: Copy delays block end-to-end testing; schema mismatches require churn.
  - Test/Verification: Run YAML validation; smoke-run bot routing on sample inputs.

## Phase 1 — Core logic
- T1.1 Data model for conversations/messages/read state
  - Goal: Persist conversations, messages, per-user read state, and support `previous_conversation_id`.
  - Inputs: Spec entities and state machine.
  - Outputs: DB schema/migrations and access layer for Conversation/Message/ReadState.
  - Steps:
    - Define tables/constraints for states and assignment exclusivity.
    - Add `previous_conversation_id` and indexes needed for list queries.
  - Done condition: Can create/read/update conversations and append messages safely.
  - Depends on: [T0.1]
  - Risks: Incorrect indexes cause slow list queries; state constraints too strict/too lax.
  - Test/Verification: Migration runs; basic CRUD tests; query plan spot-check.

- T1.2 Critical audit events + WhatsApp receipts persistence
  - Goal: Persist critical events (`TAKEN`, `REASSIGNED`, `CLOSED`, `MESSAGE_SENT_FAILED`, `LOGIN_SUCCESS`, `LOGIN_FAIL`) and message receipts (`sent/delivered/read/failed`) without UI.
  - Inputs: Spec decision log for audit/receipts.
  - Outputs: Tables + write paths for ConversationEvent and MessageReceipt.
  - Steps:
    - Define event/receipt schemas and retention assumptions (if any).
    - Ensure event writes occur on take/reassign/close/auth failures and send failures.
  - Done condition: Events/receipts are stored and queryable by `conversation_id` / `whatsapp_message_id`.
  - Depends on: [T1.1]
  - Risks: Over-logging sensitive data; missing correlation ids.
  - Test/Verification: Unit tests for event emission; integration test for receipt persistence.

- T1.3 Auth (session-based) + authorization rules
  - Goal: Implement login/logout with sessions and enforce role + conversation-based access.
  - Inputs: Roles (`agent`, `admin`), session-based auth decision.
  - Outputs: Auth endpoints, middleware/guards, and audit events for login success/fail.
  - Steps:
    - Implement session creation and secure cookie settings per environment.
    - Enforce that agents can only reply to conversations assigned to them.
    - Enforce that admins can reply only after assigning the conversation to themselves.
    - Allow `LOGIN_SUCCESS` / `LOGIN_FAIL` audit events without a `conversation_id`.
  - Done condition: Unauthorized access is blocked and audited.
  - Depends on: [T1.1, T1.2]
  - Risks: Session fixation/cookie misconfiguration; authorization gaps.
  - Test/Verification: Auth tests; role-based access tests for key endpoints.

- T1.4 Handoff state transitions (take/reassign/close)
  - Goal: Implement atomic take from `EN_ESPERA`, force-reassign (admin), and close semantics.
  - Inputs: State machine and invariants from SPEC.
  - Outputs: APIs/commands for take/reassign/close with correct locking/transactions.
  - Steps:
    - Implement atomic “take conversation” so only one agent can succeed.
    - Implement admin reassign to agents or self (not other admins) and ensure list visibility updates.
    - Allow admin to close an assigned conversation without self-assignment.
    - Implement close and ensure it disappears from all 3 tabs; create new conversation on post-close inbound with link.
  - Done condition: Concurrency tests show exclusivity; audit events are emitted.
  - Depends on: [T1.1, T1.2, T1.3]
  - Risks: Race conditions; inconsistent UI due to delayed realtime updates.
  - Test/Verification: Concurrency test for take; integration test for reassign/close.

- T1.5 Bot engine (YAML-driven) + EN_ESPERA auto-messages
  - Goal: Drive bot replies via YAML (`root` + `nodes`), with invalid input handling and handoff option action.
  - Inputs: YAML schema decision; `bot.yaml` content artifact.
  - Outputs: YAML loader/validator; routing logic for `CHATBOT`; reload endpoint (admin-only).
  - Steps:
    - Implement YAML validation and last-known-good fallback on reload.
    - Implement routing by numeric option keys; re-show menu on invalid input.
    - Implement `action: "handoff"` gating by business hours/holidays; when blocked, keep conversation in `CHATBOT` and reply with a “handoff unavailable” message.
    - Implement entry auto-reply on `EN_ESPERA` and single-shot follow-up on first inbound while waiting.
  - Done condition: End-to-end bot navigation works using the provided YAML; reload rejects invalid YAML safely.
  - Depends on: [T0.2, T1.1, T1.3]
  - Risks: YAML schema drift; accidental bot replies while assigned.
  - Test/Verification: Unit tests for routing; integration test for reload endpoint.

## Phase 2 — Integration
- T2.1 WhatsApp inbound webhook (verify + signature + idempotency)
  - Goal: Ingest inbound messages and receipts reliably and securely.
  - Inputs: WhatsApp Cloud API webhook requirements; `whatsapp_message_id` dedupe decision; optional allowlist decision.
  - Outputs: Webhook endpoints for verification handshake and message/event ingestion.
  - Steps:
    - Implement verification handshake and signature validation.
    - Implement idempotent ingestion keyed by `whatsapp_message_id`.
    - Persist inbound messages and route based on conversation state (bot/queue/assigned/closed).
  - Done condition: Duplicate deliveries do not create duplicate messages; invalid signatures are rejected.
  - Depends on: [T1.1, T1.2, T1.5]
  - Risks: Incorrect signature validation; wrong mapping of webhook payloads.
  - Test/Verification: Replay webhook payloads; signature-negative tests; dedupe tests.

- T2.2 WhatsApp outbound send (text) + receipt lifecycle
  - Goal: Send agent/bot messages to users and persist outbound attempts and receipts.
  - Inputs: WhatsApp outbound API, receipt persistence decision.
  - Outputs: Outbound send module and API endpoint used by FrontDesk.
  - Steps:
    - Implement outbound send for text.
    - Persist send result and later receipt updates (sent/delivered/read/failed).
    - Emit `MESSAGE_SENT_FAILED` audit event when appropriate.
  - Done condition: Agent can send and user receives; failure cases are persisted and auditable.
  - Depends on: [T1.2, T2.1]
  - Risks: Rate limits/timeouts; mismatch between sent message and receipts.
  - Test/Verification: Mock outbound API; simulate failures; verify receipt linking.

- T2.3 WebSocket realtime (messages + list updates)
  - Goal: Push message/list updates to FrontDesk without polling.
  - Inputs: WebSocket scope decision (no typing/presence in MVP).
  - Outputs: WebSocket server contract and client subscriptions.
  - Steps:
    - Define events: new message, conversation updated/moved between tabs.
    - Ensure updates fire on take/reassign/close and on inbound/outbound messages.
  - Done condition: UI updates near-real-time across agents/admins for the core flows.
  - Depends on: [T1.4, T2.1, T2.2]
  - Risks: Over-broadcasting; reconnect handling gaps.
  - Test/Verification: Manual multi-session test; basic WS event tests.

## Phase 3 — Observability / hardening
- T3.1 FrontDesk UI (3 tabs + 3-column layout + core actions)
  - Goal: Implement the main attention screen UX for agents/admins.
  - Inputs: UI requirements from SPEC; auth/session behavior.
  - Outputs: FrontDesk pages/components for list, chat, details panel.
  - Steps:
    - Implement login screen and session handling.
    - Implement tabs: `CHATBOT` (preview), `EN ESPERA` (preview + take), `ASIGNADOS` (chat send/receive).
    - Add canned responses and close action; add admin reassign and “assign to self”.
    - Implement unread badges and last-activity relative time display (business TZ).
  - Done condition: Core operational flow works in the browser without attachments/tipification.
  - Depends on: [T1.3, T1.4, T2.3]
  - Risks: Inconsistent authorization; UI state not matching backend races.
  - Test/Verification: Browser smoke tests; multi-agent concurrency smoke.

- T3.2 Deployment hardening (reverse proxy + allowlist toggle + config validation)
  - Goal: Ensure on-prem readiness for webhook exposure and secure defaults.
  - Inputs: Reverse proxy constraint; allowlist optional decision; session cookie settings.
  - Outputs: Deployment notes and environment flags for allowlist enablement.
  - Steps:
    - Document required reverse proxy headers and TLS termination.
    - Add allowlist configuration hooks (disabled by default).
    - Document safe cookie settings per environment.
  - Done condition: On-prem deploy has a clear runbook and secure baseline.
  - Depends on: [T2.1, T1.3]
  - Risks: Misconfiguration blocks webhook; security gaps if defaults are weak.
  - Test/Verification: Checklist-based verification in staging/on-prem.

## Phase 4 — Release / rollout
- T4.1 End-to-end acceptance run + rollback notes
  - Goal: Validate acceptance criteria and document rollback steps.
  - Inputs: ACCEPTANCE.md criteria.
  - Outputs: A repeatable validation checklist and rollback procedure.
  - Steps:
    - Run browser smoke and core flow tests (take/reassign/close, send/receive).
    - Verify audit events and receipts persistence.
    - Document rollback steps (redeploy previous image, disable reload endpoint if needed).
  - Done condition: All acceptance criteria pass (or are explicitly waived with rationale).
  - Depends on: [T3.1, T3.2]
  - Risks: Environment-specific issues; missing WhatsApp credentials prevent full validation.
  - Test/Verification: Execute the checklist in local + staging/on-prem.

## Chunking guidance
- Suggested implementation chunk size: 1–2 tasks per chunk
- Review cadence: after each chunk, verify acceptance criteria impacted by those tasks
- Stop points: safe to stop after each Phase completion (Phase 1, Phase 2, Phase 3)

## Execution status
- Status: IN_PROGRESS
- Current task: T1.5
- Completed tasks: T0.1, T0.2, T1.1, T1.2, T1.3, T1.4
- Progress: 6/13
- Last updated: 2026-02-02
