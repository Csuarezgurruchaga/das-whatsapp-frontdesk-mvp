# TASKS

## Phase 0 — Setup / scaffolding
- T0.1 Align configs, roles, and feature flags
  - Goal: Define the minimal config/roles/flags needed to ship Extras safely on-prem.
  - Inputs: `docs/specs/whatsapp-frontdesk-extensions/SPEC.md`, Core auth/roles model, deployment topology.
  - Outputs: Config list (`ATTACHMENTS_DIR`, `EXPORTS_DIR`, `EXPORTS_TTL_DAYS`), role matrix (`admin`, `supervisor`, operator), feature flags list.
  - Steps:
    - Confirm how `admin`/`supervisor` roles are represented in Core.
    - Define feature flags for attachments, exports, hard delete, taxonomy admin UI.
    - Document the required env vars and defaults.
  - Done condition: Config/roles/flags are explicitly documented and referenced by all later tasks.
  - Depends on: []
  - Risks: Misaligned role semantics causes accidental privilege escalation.
  - Test/Verification: Review role matrix with stakeholders; verify flags can disable UI entrypoints.

## Phase 1 — Core logic
- T1.1 Implement attachment metadata model
  - Goal: Persist attachment metadata needed for history display, authorization, and downloads.
  - Inputs: Conversation/message identifiers from Core, DB access patterns in Core.
  - Outputs: Attachment metadata persistence (schema/model + CRUD).
  - Steps:
    - Define fields: conversation_id, message_id, attachment_id, original_filename, mime, size_bytes, storage_relpath, status, created_by, created_at.
    - Add indexes for conversation_id and message_id.
  - Done condition: Attachments can be created/read by conversation_id and are stable across retries.
  - Depends on: [T0.1]
  - Risks: Incomplete fields block later download/export.
  - Test/Verification: DB migration/model tests; create/read roundtrip.

- T1.2 Implement `safe(truncate(filename))` + MIME validation
  - Goal: Enforce consistent filename sanitization and allowlist validation per SPEC.
  - Inputs: SPEC rules (NFC normalize, separator/path traversal removal, `_` replacement, 120 chars preserving extension; allowlist + extension fallback).
  - Outputs: Reusable library functions for filename handling and MIME/extension validation.
  - Steps:
    - Implement sanitize/truncate routine.
    - Implement allowlist validation with fallback by extension when MIME is empty or `application/octet-stream`.
    - Add constants for Meta Cloud API constraints (100MB max + MIME list + per-media-type caps).
  - Done condition: Library functions cover edge cases and match SPEC.
  - Depends on: [T0.1]
  - Risks: Incorrect normalization/escaping can allow path injection or break downloads.
  - Test/Verification: Unit tests covering separators, `..`, long names, Unicode, octet-stream fallback, allowlist behavior, and per-type size caps (image/audio/video/document).

- T1.3 Implement attachment binary storage on NAS
  - Goal: Store uploaded binaries under `ATTACHMENTS_DIR/<conversation_id>/<attachment_id>_<safe(truncate(original))>`.
  - Inputs: `ATTACHMENTS_DIR`, attachment_id generation strategy, sanitize routine.
  - Outputs: Storage write/read helpers; creation of required directories; consistent relpath stored in metadata.
  - Steps:
    - Ensure folder-per-conversation creation is safe and idempotent.
    - Write file atomically (temp + rename) to avoid partial writes.
    - Record relpath in metadata (for later `X-Accel-Redirect` mapping).
  - Done condition: Files appear in NAS layout and metadata points to correct relpath.
  - Depends on: [T1.1, T1.2]
  - Risks: Partial writes, permissions errors, path mismatches between app and proxy mounts.
  - Test/Verification: Integration test writes a file and validates it exists on disk; simulate permission errors.

- T1.4 Implement attachment upload + send pipeline (WhatsApp native media)
  - Goal: Operator uploads attachment, system stores and sends it via Meta Cloud API as native media.
  - Inputs: Existing WhatsApp Cloud API integration in Core, attachment storage + metadata.
  - Outputs: Backend endpoint(s) for upload; send job/action; status updates.
  - Steps:
    - Validate size/MIME before accepting upload.
    - Store binary + metadata; create a message-history entry referencing attachment.
    - Send via WhatsApp; update status (sent/failed).
  - Done condition: Upload results in WhatsApp delivery attempt and UI-visible final status.
  - Depends on: [T1.1, T1.2, T1.3]
  - Risks: Provider errors; retry/idempotency causing duplicate sends.
  - Test/Verification: Stub/fixture provider responses; verify status transitions and dedupe/retry behavior.

- T1.5 Implement export ZIP generation (on-demand)
  - Goal: Generate ZIP with JSON transcript + attachments only when requested by admin/supervisor.
  - Inputs: Message history retrieval in Core, attachment metadata and binaries, `EXPORTS_DIR`.
  - Outputs: Export generator producing a ZIP at a predictable path; export record/metadata (optional).
  - Steps:
    - Create JSON transcript format (minimal and stable).
    - Add attachment binaries to ZIP (or references if missing, with warnings).
    - Write ZIP to `EXPORTS_DIR` and return an export identifier/path.
  - Done condition: For a conversation, export generates a ZIP that includes transcript + expected attachments.
  - Depends on: [T1.1, T1.3]
  - Risks: Large exports cause timeouts; missing files; path traversal inside ZIP.
  - Test/Verification: Integration test for small conversation; validate ZIP contents; ensure filenames in ZIP are safe.

- T1.6 Implement exports TTL cleanup
  - Goal: Remove expired exports according to `EXPORTS_TTL_DAYS` (default 7).
  - Inputs: `EXPORTS_DIR`, `EXPORTS_TTL_DAYS`.
  - Outputs: Cleanup job/command and logs for deletions.
  - Steps:
    - Define timestamp source (file mtime or export metadata).
    - Delete expired ZIPs and empty folders.
  - Done condition: Old exports are removed and recent exports remain.
  - Depends on: [T1.5]
  - Risks: Accidentally deleting non-export files; timezone edge cases.
  - Test/Verification: Unit tests with fake timestamps; dry-run mode for staging.

- T1.7 Implement hard delete + deletion event
  - Goal: Admin can hard delete a conversation’s artifacts and record a minimal deletion event.
  - Inputs: Conversation/message deletion capability in Core, attachment metadata/binaries, optional reason text.
  - Outputs: Deletion handler that removes data and writes deletion event (conversation_id, actor, timestamp, optional reason).
  - Steps:
    - Authorize admin-only action.
    - Delete attachment binaries + metadata + any export artifacts as applicable.
    - Delete conversation/messages per Core rules.
    - Write deletion event without message contents/binaries.
  - Done condition: Conversation is deleted, files are removed, and deletion event exists.
  - Depends on: [T1.1, T1.3, T0.1]
  - Risks: Orphaned files; accidental deletion; partial failure mid-delete.
  - Test/Verification: Integration test deletes a seeded conversation and validates cleanup; verify event is recorded.

## Phase 2 — Integration
- T2.1 Implement reverse-proxy download/view path via `X-Accel-Redirect`
  - Goal: Serve attachment and export downloads through proxy after backend authorization, without streaming.
  - Inputs: Attachment/export relpaths, proxy config support for internal locations, app session auth.
  - Outputs: Backend endpoints that authorize and respond with `X-Accel-Redirect`; documented proxy configuration.
  - Steps:
    - Implement authorize endpoint for `attachment_id` download/view.
    - Implement authorize endpoint for export download.
    - Document required Nginx/Apache config (internal location, root mapping, headers).
  - Done condition: Downloads work end-to-end in staging with shared SSO/session.
  - Depends on: [T1.1, T1.3, T1.5]
  - Risks: Proxy misconfig leaks files; mount path mismatch; cache issues.
  - Test/Verification: Manual staging test + access-control checks (403 when unauthorized).

- T2.2 Implement frontend attachments UI (composer + history + view/download)
  - Goal: Match the existing UI pattern: paperclip in composer; message bubble display; view/download controls.
  - Inputs: Existing frontend architecture, API endpoints for upload/status/download/view.
  - Outputs: UI changes for attachments: upload entrypoint, status display, view modal/iframe for supported types.
  - Steps:
    - Add paperclip action in composer with file picker.
    - Show `uploading` state and final `sent/failed`.
    - Render attachment messages in history with icon/filename/size/status.
    - Add View + Download (PDF/PNG/JPG/JPEG/TXT), Download only for others.
  - Done condition: Operator can upload, see status, and open view/download flows.
  - Depends on: [T1.4, T2.1]
  - Risks: Browser preview issues; inconsistent MIME typing client-side.
  - Test/Verification: Browser smoke in Chromium; upload small PDF/JPG/TXT and verify view; verify unsupported types only download.

- T2.3 Implement tipification UI (tags) + taxonomy admin UI
  - Goal: Allow operators to tag conversations and admins to manage taxonomy; supervisors have read-only admin UI.
  - Inputs: Existing UI details panel patterns; backend endpoints for tags and taxonomy.
  - Outputs: Conversation tags UI; taxonomy admin page; role gating.
  - Steps:
    - Add tag selector in conversation details.
    - Implement admin taxonomy CRUD UI (with archive/disable and rename).
    - Implement supervisor read-only access (view list, no edits).
  - Done condition: Tags work end-to-end and admin UI respects roles.
  - Depends on: [T0.1]
  - Risks: Governance drift; UI complexity.
  - Test/Verification: Manual role-based checks for operator/admin/supervisor; verify rename migrates references.

## Phase 3 — Observability / hardening
- T3.1 Add logs/metrics and operator-facing errors
  - Goal: Make failures diagnosable and UX clear for operators.
  - Inputs: Existing logging/metrics patterns in Core.
  - Outputs: Structured logs/metrics for upload validation, send results, download failures, export failures, deletes.
  - Steps:
    - Add metrics counters for send success/failure.
    - Add logs for proxy auth denials and missing files.
    - Add UI error messages for invalid uploads and send failures.
  - Done condition: Dashboards/log queries can identify common failure modes.
  - Depends on: [T1.4, T2.1, T1.5, T1.7]
  - Risks: Noisy logs; missing correlation IDs.
  - Test/Verification: Trigger known failures in staging; verify logs/metrics are emitted.

## Phase 4 — Release / rollout
- T4.1 Staging validation + rollout checklist
  - Goal: Validate on-prem deployment readiness and define rollback.
  - Inputs: Staging environment matching production (NAS + proxy + SSO), feature flags.
  - Outputs: Rollout checklist; rollback steps; operator/admin short guide.
  - Steps:
    - Validate uploads/downloads/views, exports, hard delete, taxonomy permissions.
    - Validate cleanup job and TTL behavior.
    - Confirm feature flags can disable all Extras.
  - Done condition: Stakeholders sign off on acceptance criteria and rollout plan.
  - Depends on: [T2.2, T2.3, T1.6, T1.7]
  - Risks: Environment drift between staging and prod.
  - Test/Verification: Run acceptance checklist in Chromium; verify proxy auth works for unauthorized users.

## Chunking guidance
- Suggested implementation chunk size: 1–2 tasks per chunk
- Review cadence: after each chunk, verify acceptance criteria impacted by those tasks
- Stop points: safe to stop after Phase 0, after Phase 1 (core backend), after Phase 2 (UI + proxy), after Phase 3 (observability)

## Execution status
- Status: IN_PROGRESS
- Current task: T4.1
- Completed tasks: T0.1, T1.1, T1.2, T1.3, T1.4, T1.5, T1.6, T1.7, T2.1, T2.2, T2.3, T3.1
- Progress: 12/13
- Last updated: 2026-02-06
- Notes: T4.1 rollout/rollback/operator guide drafted in `DEPLOYMENT.md`; staging acceptance run and stakeholder sign-off remain pending.
