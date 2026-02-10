# SPEC (Draft) — WhatsApp FrontDesk Extensions (Extras)

## Summary
This spec defines “extras” that extend `whatsapp-frontdesk-mvp` after the Core MVP is stable.
Focus areas include attachments and tipification, plus any additional hardening that is intentionally excluded from the Core spec.

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

## Goals / Non-goals
### Goals (Spec B)
- Attachments:
  - operator can upload a file,
  - system persists it in an on-prem compatible storage (NAS-mounted directory),
  - message history references the attachment,
  - send via WhatsApp as **native media** (no “send as link” in scope).
- Tipification:
  - operator can tag/categorize a conversation,
  - tipification is visible in details panel,
  - tipification is **not** required to close a conversation (per Core decision).
- Realtime hardening and fallback strategies if needed (polling/SSE fallback).

### Non-goals (Spec B)
- New dashboards/reports beyond what is required to support the above.
- Full multi-tenant separation.

## Constraints
- Must remain on-prem compatible (filesystem/NAS or S3-compatible on-prem, e.g., MinIO).
- Must integrate cleanly with the data model and flows from `docs/specs/whatsapp-frontdesk-mvp/SPEC.md`.
- Attachment storage directory must be configurable per deployment via `ATTACHMENTS_DIR`:
  - local/dev: a local folder
  - production: a NAS-mounted folder

## Key Flows
1) Upload attachment → persist → reference in message history → deliver to user (WhatsApp).
2) Tipify conversation → persist → show in details panel → use for audit/reporting later.
3) Admin operations: export conversation (ZIP) and hard delete, as needed.

## Data / Interfaces
### Attachments
- Storage: filesystem directory (NAS-mounted in production), configured via `ATTACHMENTS_DIR`.
- Delivery: WhatsApp native media only.
- Policy: enforce “official WhatsApp constraints” (type/size) and block invalid files before upload.
- UX for invalid files: block before upload when the file violates known WhatsApp constraints (type/size) and show a clear error to the operator.
- WhatsApp Cloud API constraints (Meta) — soft hardcode as constants (not per-deployment config):
  - `MAX_UPLOAD_BYTES = 100MB` (overall upload limit).
  - Supported MIME allowlist (initial draft):
    - Images: `image/jpeg`, `image/png`
    - Video: `video/mp4`, `video/3gp`, `video/3gpp`
    - Audio: `audio/aac`, `audio/amr`, `audio/mp4`, `audio/ogg`, `audio/mpeg`
    - Text/PDF: `text/plain`, `application/pdf`
    - Office legacy: `application/msword`, `application/vnd.ms-excel`, `application/vnd.ms-powerpoint`
    - Office OOXML: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/vnd.openxmlformats-officedocument.presentationml.presentation`
  - Notes:
    - `audio/ogg` is expected to be Opus; non-Opus OGG may be rejected by WhatsApp.
    - Some references list 3GP as `video/3gp` (vs `video/3gpp`). Treat both as acceptable if encountered.
    - Images are typically expected to be 8-bit, RGB or RGBA.
    - Meta references commonly describe size limits by media type. This spec enforces these per-type caps at upload time to prevent predictable send failures.
    - Size limits (enforced by this spec):
      - image: 5MB
      - audio: 16MB
      - video: 16MB
      - document: 100MB
  - Validation strategy: enforce `MAX_UPLOAD_BYTES` + MIME allowlist + per-media-type size caps above.
  - Source of truth: Meta WhatsApp Business Platform / Cloud API docs, **as of 2026-01-30**.
    - Primary URL (provided): https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/media
    - Secondary reference: Meta-maintained WhatsApp Business Platform Postman collection (practical cross-check).
- UI entrypoint: paperclip (clip) icon inside the message composer (see `UI-adjunto.png`).
- UI states (MVP): `uploading → sent/failed` (no explicit intermediate stored/sending states in UI).
- Display in history: message bubble with attachment icon + filename + size + status (sent/failed).
- Download behavior (as selected): reverse-proxy (Nginx/Apache) serves files from a NAS-mounted directory (read-only mount on the proxy host).
- View behavior (hybrid on top of reverse-proxy):
  - PDF/PNG/JPG/JPEG/TXT: show “View” (modal/iframe) + “Download”
  - DOCX/XLSX/PPTX: “Download” only
- Reverse-proxy details:
  - AuthN/AuthZ: use the same SSO/session as the app (downloads are requested through the app backend, which authorizes using the normal session, and delegates file serving to the proxy).
  - URL mapping: downloads are addressed by opaque `attachment_id`; the backend authorizes and responds with `X-Accel-Redirect` (internal redirect; no app streaming).
- Attachment immutability: attachments are immutable once uploaded (no replace/update; re-upload creates a new attachment message).
- Storage layout (NAS): `/<conversation_id>/<attachment_id>_<safe(truncate(original_filename))>`.
  - `safe(truncate(original_filename))` rule:
    - Normalize to NFC (Unicode).
    - Remove path traversal and separators (treat `/`, `\`, and sequences like `..` as invalid).
    - Replace unsafe characters with `_`.
    - Truncate base name to 120 chars while preserving extension.
- Metadata model: to be defined (see Open Questions) but must minimally support:
  - original filename
  - content type (MIME)
  - size (bytes)
  - storage path (relative to `ATTACHMENTS_DIR`)
  - message/conversation references
  - upload actor + timestamps
- MIME fallback: if browser reports empty MIME or `application/octet-stream`, infer MIME by file extension (allowlist-driven); otherwise, enforce MIME strictly.

### Tipification
- Model: multiple tags per conversation.
- Taxonomy management: admin UI (CRUD) in scope.
- Current operational scope uses only two roles: `agent` and `admin`.
- Taxonomy admin is `admin` only; `agent` has no taxonomy-admin access.
- Audit: store only current tags (no historical audit trail in scope).
- Export: per-conversation manual export in scope as a ZIP including JSON transcript + attachments.
  - Generation: on-demand only (generated when requested).
  - Storage: `EXPORTS_DIR` (separate from `ATTACHMENTS_DIR`).
  - Serving: via reverse-proxy (same infra pattern as attachments; no app streaming).
  - Permissions: admin only.
  - Retention: TTL + cleanup job, configurable via `EXPORTS_TTL_DAYS` (default: 7 days).
- Taxonomy lifecycle: allow renaming tags (migrate references); do not allow deletion (use “archived/disabled” instead).

## Edge cases & Failure modes
- Large files, unsupported types, WhatsApp send failures.
- Storage unavailability (NAS/MinIO downtime).
- Retention/cleanup policy.

## Observability
- Attachment send failure rates, storage errors.
- Tipification audit events.

## Security / Privacy
- Attachment access control: downloads go through reverse-proxy (no app backend streaming). Authorization is enforced by infrastructure (proxy auth, sharing the app session) plus app-level UI visibility rules.
- PII retention policy for attachment contents.
- Hard delete is an admin-only action exposed in the conversation details UI.
- Hard delete audit: record a minimal “deletion event” (conversation_id, actor, timestamp, optional reason) without retaining message contents or attachment binaries.

## Open Questions
None (as of 2026-01-30).

## Decision Log
- 2026-01-29 — Created as a draft placeholder due to spec split (Core vs Extras).
- 2026-01-30 — Storage: filesystem/NAS via `ATTACHMENTS_DIR`; delivery: WhatsApp native media only; no AV scan; tipification: multiple tags with admin UI; retention: indefinite until manual delete; export: manual per conversation.
  - Rationale:
    - On-prem simplicity (NAS mount) and minimal infra assumptions.
    - Preserve WhatsApp UX by using native media and avoid link-delivery complexity.
    - Defer advanced hardening (AV, extra policy rules) until demanded by a concrete compliance need.
- 2026-01-30 — Attachments: block before upload when file violates known WhatsApp constraints (type/size).
  - Rationale:
    - Prevent predictable failures and reduce operator frustration/support load.
- 2026-01-30 — Attachments UI: paperclip in composer; states: `uploading → sent/failed`; displayed as message bubbles; dedupe: none.
  - Rationale:
    - Match the existing UI affordance (`UI-adjunto.png`) and keep MVP UI/state machine simple.
- 2026-01-30 — Downloads: reverse-proxy serves NAS-mounted (read-only) files; hybrid view/download UX by file type.
  - Rationale:
    - Enable in-browser downloads without adding custom backend streaming logic.
    - Keep storage on NAS while allowing controlled HTTP access via infrastructure.
- 2026-01-30 — Reverse-proxy: shared SSO/session; opaque `attachment_id` URLs; previews include TXT and JPEG.
  - Rationale:
    - Avoid exposing real filesystem paths and keep authorization aligned with the app session.
    - Support common “quick view” formats in the operator UI without adding Office preview complexity.
- 2026-01-30 — Storage layout: per-conversation folder; export ZIP generated on-demand; export retention via TTL cleanup; export permission admin-only (current operational scope).
  - Rationale:
    - Keep NAS storage organized and make per-conversation cleanup straightforward.
    - Avoid unnecessary storage growth by generating exports only when requested.
- 2026-01-30 — Tipification: no history; export: ZIP (JSON transcript + attachments).
  - Rationale:
    - Keep data model simple; introduce audit trail only if compliance demands it.
    - Enable pragmatic per-case export for support/audit needs.
- 2026-01-30 — Admin controls: taxonomy admin is admin-only; retention delete is admin-only hard delete.
  - Rationale:
    - Reduce governance drift and simplify permissions for the first iteration.
- 2026-01-30 — Tipification taxonomy lifecycle: rename allowed (migrate references); deletion not allowed (archive/disable instead).
  - Rationale:
    - Preserve reporting stability and avoid breaking historical classification while still allowing corrections.
- 2026-01-30 — WhatsApp constraints: “soft hardcode” constants for Meta WhatsApp Cloud API (100MB max, MIME allowlist, and per-type size caps).
  - Rationale:
    - Keep behavior consistent across deployments while making limits easy to adjust in code if Meta/provider changes.
- 2026-01-30 — Finalized details: attachments immutable; NAS naming uses `attachment_id + safe(truncate(original_filename))`; MIME fallback by extension for empty/octet-stream; export TTL configurable via `EXPORTS_TTL_DAYS` (default 7); taxonomy admin is admin-only in the current two-role scope (`agent`/`admin`); hard delete writes minimal deletion event.
  - Rationale:
    - Improve interoperability with real-world browser MIME behavior while staying allowlist-driven.
    - Keep governance and auditability without retaining PII in deletion logs.
- 2026-01-30 — Meta constraints review: include `audio/amr`; document OGG/Opus caveat; acknowledge `video/3gp` vs `video/3gpp`; enforce per-type size caps at upload time.
  - Rationale:
    - Align allowlist and caps with common Meta-aligned references to reduce avoidable send failures.
- 2026-01-30 — Attachments: immutable; NAS naming uses `attachment_id + safe(truncate(original_filename))`; validation enforces `MAX_UPLOAD_BYTES` + MIME allowlist + per-type caps; Office MIME supports legacy + OOXML; `X-Accel-Redirect` path resolved via DB lookup in backend.
  - Rationale:
    - Keep storage references stable (immutable) and simplify retry/idempotency behavior.
    - Preserve usability in file shares while avoiding filesystem/path injection risk.
    - Prevent predictable send failures by enforcing per-type caps pre-upload.
- 2026-01-30 — Exports: ZIP generated on-demand only; stored under `EXPORTS_DIR`; served via reverse-proxy; export permission is admin-only in the current two-role scope (`agent`/`admin`); export retention uses TTL cleanup (default 7 days); hard delete action lives in conversation details.
  - Rationale:
    - Generate exports only when needed to control storage growth.
    - Separate exports from attachments for quota/permissions management.

## Changelog
- 2026-01-29 — Initial draft created.
  - reason: enforce scope boundary vs `whatsapp-frontdesk-mvp`
  - impact: requires dedicated spec-interview rounds to finalize
- 2026-01-30 — Enforce per-type size caps at upload time.
  - reason: prevent predictable WhatsApp send failures (decision change)
  - impact: update validation logic/tests and acceptance criteria (A1)

## Glossary
- **MinIO:** an S3-compatible object storage typically deployed on-prem.
- **ATTACHMENTS_DIR:** deployment config pointing to the on-disk directory where uploaded attachment binaries are stored (local in dev, NAS-mounted in prod).
- **NAS:** network-attached storage. In practice, a shared filesystem mounted via SMB/NFS in on-prem environments.
- **Reverse-proxy:** an HTTP proxy (e.g., Nginx/Apache) used to serve downloads from NAS storage, enforcing auth outside the app backend.
- **X-Accel-Redirect:** an Nginx feature where the backend authorizes a request, then instructs Nginx to serve a file via an internal path without streaming through the backend.
