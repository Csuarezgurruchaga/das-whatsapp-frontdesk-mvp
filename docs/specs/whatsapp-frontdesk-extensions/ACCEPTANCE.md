# ACCEPTANCE — WhatsApp FrontDesk Extensions (Extras)

## A0 — Browser smoke (web)
- The app loads in Chromium without critical console errors.
- The primary happy-path flow works end-to-end in the browser.

## A1 — Attachments: upload, validate, send, and status
- From the composer (paperclip icon), an operator can upload an attachment.
- Invalid files are blocked before upload based on Meta Cloud API constraints:
  - 100MB max + MIME allowlist
  - per-media-type size caps (image 5MB, audio/video 16MB, document 100MB)
  - extension fallback only when MIME is empty/octet-stream
- After upload, the attachment is sent via WhatsApp as native media.
- UI shows `uploading → sent/failed` and the final status is persisted.

## A2 — Attachments: history rendering
- Attachment messages appear in the message history as a message bubble including icon, filename, size, and status.

## A3 — Attachments: view/download via reverse-proxy (no streaming)
- Download and view requests are authorized by the backend using the normal app session.
- Backend delegates file serving via `X-Accel-Redirect` (or equivalent internal redirect) and does not stream binaries.
- “View” works for PDF/PNG/JPG/JPEG/TXT in a modal/iframe; other types offer “Download” only.

## A4 — Tipification: tagging conversations
- A conversation supports multiple tags; tags are visible in the details panel.
- Tags are not required to close a conversation.

## A5 — Taxonomy admin UI: roles and lifecycle
- `admin` can create/edit/rename/archive tags in the taxonomy admin UI.
- `agent` cannot manage taxonomy admin (taxonomy admin is restricted to `admin`).
- Tag rename migrates references; deletion is not allowed (archive/disable instead).

## A6 — Export ZIP: on-demand, permissions, retention
- `admin` can request an on-demand export ZIP per conversation.
- `agent` cannot request/export ZIPs.
- Export ZIP contains JSON transcript + attachments and is stored under `EXPORTS_DIR`.
- Export ZIP is served via reverse-proxy after backend authorization (same pattern as attachments).
- Exports expire and are cleaned up using `EXPORTS_TTL_DAYS` (default 7).

## A7 — Hard delete: admin-only with minimal audit
- Hard delete is available in conversation details and restricted to `admin`.
- Hard delete removes attachment binaries, attachment metadata, and conversation/message records per Core rules.
- A minimal deletion event is recorded (conversation_id, actor, timestamp, optional reason) without retaining message contents or binaries.
