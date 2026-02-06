# PLAN — WhatsApp FrontDesk Extensions (Extras)

This plan implements the “Extras” on top of `whatsapp-frontdesk-mvp` once the Core MVP is stable.

## Milestones

### M0 — Alignment & prerequisites
- Confirm Core provides required primitives: conversation IDs, message history, operator auth/session, and a stable UI composer area.
- Confirm on-prem deployment topology: NAS mount points, reverse-proxy (Nginx/Apache) placement, and shared SSO/session integration.

### M1 — Attachments (upload → send → history → view/download)
- Implement attachment upload from the composer (paperclip).
- Persist attachment binaries to `ATTACHMENTS_DIR` on NAS using the agreed naming scheme.
- Persist attachment metadata (MIME, size, original filename, conversation/message references).
- Validate pre-upload using Meta Cloud API constraints (soft hardcoded constants), including per-media-type size caps.
- Send attachments via WhatsApp as native media and reflect result in UI (`uploading → sent/failed`).
- Implement attachment display in message history as a message bubble (icon + filename + size + status).
- Serve view/download via reverse-proxy with `X-Accel-Redirect` after backend authorization (no streaming).
- Support “View” for PDF/PNG/JPG/JPEG/TXT, “Download” for others.

### M2 — Tipification (tags) + taxonomy admin UI
- Implement tagging of conversations (multiple tags).
- Create taxonomy management UI (CRUD) restricted to `admin`, with `supervisor` read-only access.
- Enforce lifecycle rules: rename allowed (migrates references), delete not allowed (archive/disable).

### M3 — Export ZIP (per conversation) + retention
- Implement on-demand export: ZIP containing JSON transcript + attachments.
- Store exports under `EXPORTS_DIR`, serve via reverse-proxy (same pattern as attachments).
- Restrict export permissions to `admin` + `supervisor`.
- Implement export retention with TTL cleanup (`EXPORTS_TTL_DAYS`, default 7).

### M4 — Admin hard delete + audit event
- Add admin-only hard delete action in conversation details.
- Delete binaries + metadata + references.
- Record minimal deletion event (conversation_id, actor, timestamp, optional reason), without retaining message contents or binaries.

## Dependencies / prerequisites
- WhatsApp Cloud API integration exists in Core (auth/credentials, send message pipeline), or is added as a prerequisite task here.
- A persistence layer exists (DB) to store attachment metadata, tags, taxonomy, deletion events.
- Reverse-proxy supports `X-Accel-Redirect` (Nginx) or an equivalent mechanism; if Apache is used, confirm equivalent internal redirect approach.

## Observability & operations
- Add logs/metrics for:
  - upload validation failures (type/size)
  - WhatsApp send success/failure rates for attachments
  - reverse-proxy download/view 4xx/5xx rates
  - export job duration/failures and cleanup results
  - deletion events (counts, actors)
- Add operator-facing error messages for failed sends and unsupported uploads.

## Rollout / rollback
- Feature-flag attachments UI entrypoint and export/hard delete actions.
- Rollback strategy: disable feature flags; keep stored binaries/metadata unchanged.
- Validate on a staging on-prem environment with NAS + reverse-proxy config matching production.

## Test strategy (high-level)
- Unit tests for:
  - filename sanitization (`safe(truncate(...))`)
  - MIME allowlist + extension fallback behavior
  - TTL cleanup logic for exports
- Integration tests for:
  - attachment upload → persisted file exists → metadata saved
  - backend authorize + `X-Accel-Redirect` header issuance
  - export ZIP contains expected transcript + binaries
- Manual smoke checks in browser for the primary flows.
