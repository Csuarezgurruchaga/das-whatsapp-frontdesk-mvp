# DEPLOYMENT — WhatsApp FrontDesk Extensions

## Acceptance run checklist

Last updated: 2026-02-09

### Scope
- Validate `docs/specs/whatsapp-frontdesk-extensions/ACCEPTANCE.md` criteria A0-A7.
- Execute in both local and staging/on-prem environments.
- Current operational scope for this acceptance run: 2 roles (`admin`, `agent`). `supervisor` remains legacy in code/DB but is out of scope.

### Prereqs
- App is running with DB migrated.
- Roles are seeded for `agent` and `admin` (current operational scope).
- Feature flags are configured:
  - `FEATURE_ATTACHMENTS_ENABLED`
  - `FEATURE_EXPORTS_ENABLED`
  - `FEATURE_HARD_DELETE_ENABLED`
  - `FEATURE_TAXONOMY_ADMIN_ENABLED`
- Filesystem paths are configured and writable by app/proxy:
  - `ATTACHMENTS_DIR`
  - `EXPORTS_DIR`
- Reverse proxy internal redirects are configured as documented in `docs/specs/whatsapp-frontdesk-extensions/PROXY.md`.
- WhatsApp Cloud API credentials are available for send-path validation.

### Execution record
- Local: COMPLETE (SQLite + direct app server; reverse proxy not configured locally, so internal redirect serving is waived but headers/authorization are still verified).
- Staging/on-prem: PENDING (required for final sign-off).

### Local baseline verification (automated)
- `.venv/bin/python -m unittest discover -s tests -v`
  - Evidence log: `/tmp/wfdx-acceptance/unittest-20260209.txt`
- `node --check app/static/app.js`

### Checklist template (run per environment)
#### A0 - Browser smoke (web)
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - Screenshots:
    - `/tmp/wfdx-acceptance/a0-smoke-desktop.png`
    - `/tmp/wfdx-acceptance/a0-smoke-mobile.png`
  - Console log: `/tmp/wfdx-acceptance/a0-console.txt`
  - Notes:
    - Console includes `401 /auth/me` before login (expected on cold start) and `404 /favicon.ico` (cosmetic). No post-login critical errors observed.
- Steps:
  - Open `/` in Chromium.
  - Login as `admin`.
  - Navigate to at least one conversation and verify UI renders lists/chat/detail without critical errors.

#### A1 - Attachments upload/validation/send/status
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - Validation rejections (curl evidence):
    - Invalid MIME rejected: `HTTP 400` (`Unsupported MIME type: application/x-msdownload`).
      - Evidence: `/tmp/wfdx-acceptance/a1-invalid-mime.headers` + `/tmp/wfdx-acceptance/a1-invalid-mime.body`
    - Oversize image rejected: `HTTP 400` (`Attachment exceeds the image limit of 5242880 bytes`).
      - Evidence: `/tmp/wfdx-acceptance/a1-image-too-big.headers` + `/tmp/wfdx-acceptance/a1-image-too-big.body`
  - Local note: WhatsApp credentials are dummy in `.env.sqlite`, so send attempts fail upstream; final `failed` state is persisted and rendered in UI.
    - Evidence: `/tmp/wfdx-acceptance/a2-send.headers` + `/tmp/wfdx-acceptance/a2-send.body`
    - UI bubble evidence: `/tmp/wfdx-acceptance/a2-chat-messages-desktop.png`
  - Automated validation coverage:
    - `tests/test_attachment_validation.py` (see `/tmp/wfdx-acceptance/unittest-20260209.txt`)
- Steps:
  - Upload valid files from composer (paperclip) for image, audio/video, and document classes.
  - Confirm blocked uploads for invalid MIME and oversize constraints (100MB max + per-type caps).
  - Confirm MIME extension fallback applies only when browser MIME is empty/octet-stream.
  - Confirm status transitions `uploading -> sent/failed` and the final status is persisted.

#### A2 - Attachments history rendering
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - UI evidence (bubble): `/tmp/wfdx-acceptance/a2-chat-messages-desktop.png`
  - Full-page context: `/tmp/wfdx-acceptance/a0-a2-desktop.png`
  - Backend message listing: `/tmp/wfdx-acceptance/messages-2-after-a2.json`
- Steps:
  - Confirm history bubble renders attachment icon, filename, size, and status.
  - Confirm failed sends remain visible with failure status.

#### A3 - Reverse-proxy view/download authorization
- Status: [ ] PASS [ ] FAIL [x] WAIVED (reason)
- Evidence/notes:
  - WAIVED (local environment): no reverse proxy configured; endpoints return `X-Accel-Redirect` headers but file serving via internal redirect requires Nginx mapping per `docs/specs/whatsapp-frontdesk-extensions/PROXY.md`.
  - Backend authorization endpoint evidence (local):
    - Attachment download (admin): `HTTP 200` + `X-Accel-Redirect` header.
      - Evidence: `/tmp/wfdx-acceptance/a3-attach-admin.headers`
    - Attachment download (agent denied): `HTTP 403`.
      - Evidence: `/tmp/wfdx-acceptance/a3-attach-agent.headers` + `/tmp/wfdx-acceptance/a3-attach-agent.body`
    - Export download (admin): `HTTP 200` + `X-Accel-Redirect` header.
      - Evidence: `/tmp/wfdx-acceptance/a6-admin.headers`
    - Export download (agent denied): `HTTP 403`.
      - Evidence: `/tmp/wfdx-acceptance/a6-agent.headers` + `/tmp/wfdx-acceptance/a6-agent.body`
- Steps:
  - From an authorized session, confirm `View`/`Download` endpoints return internal redirect response headers (no backend file streaming).
  - Confirm unauthorized/forbidden roles get access denied on attachment/export authorization endpoints.
  - In staging/on-prem with proxy configured, verify the proxy actually serves the binaries for `View` and `Download`.

#### A4 - Tipification tags in conversation details
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - Automated regression coverage: `/tmp/wfdx-acceptance/unittest-20260209.txt`
    - `tests/test_taxonomy_and_tags.py::TestTaxonomyAndTags::test_agent_can_set_conversation_tags_and_read_detail`
- Steps:
  - Assign multiple tags to a conversation and confirm persistence on refresh.
  - Confirm tags are visible in conversation details.
  - Confirm close-conversation flow does not require tags.

#### A5 - Taxonomy admin role/lifecycle checks
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - Automated regression coverage: `/tmp/wfdx-acceptance/unittest-20260209.txt`
    - Admin lifecycle: `tests/test_taxonomy_and_tags.py::TestTaxonomyAndTags::test_admin_can_create_rename_and_archive_tag`
    - Agent denied: `tests/test_taxonomy_and_tags.py::TestTaxonomyAndTags::test_create_taxonomy_tag_requires_admin`
- Steps:
  - As `admin`, create, rename, and archive/disable tags.
  - As `agent`, verify taxonomy admin actions are not available (or fail with access denied).
  - Confirm rename migrates existing conversation tag references.

#### A6 - Export ZIP generation/permissions/retention
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - Export download authorization:
    - Admin authorized: `HTTP 200` + `X-Accel-Redirect: /_internal/exports/2/conversation-2-a6local1.zip`.
      - Evidence: `/tmp/wfdx-acceptance/a6-admin.headers`
    - Agent denied: `HTTP 403`.
      - Evidence: `/tmp/wfdx-acceptance/a6-agent.headers` + `/tmp/wfdx-acceptance/a6-agent.body`
  - ZIP content (transcript + attachments) is covered by unit tests:
    - `tests/test_export_pipeline.py::TestExportPipeline::test_generate_export_zip_includes_transcript_and_attachment_binary` (see `/tmp/wfdx-acceptance/unittest-20260209.txt`)
  - Retention cleanup is covered by unit tests:
    - `tests/test_export_cleanup.py` (see `/tmp/wfdx-acceptance/unittest-20260209.txt`)
  - Local-only note: export ZIP used as a deterministic fixture at `./.runtime/exports/2/conversation-2-a6local1.zip`.
- Steps:
  - As `admin`, request export for a conversation.
  - Verify ZIP contains JSON transcript and expected attachments.
  - Confirm export download is authorized and served through reverse-proxy path.
  - Validate retention behavior with `EXPORTS_TTL_DAYS` (dry-run first, then real cleanup in non-prod).

#### A7 - Hard delete and minimal deletion audit
- Status: [x] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
  - Automated regression coverage: `/tmp/wfdx-acceptance/unittest-20260209.txt`
    - `tests/test_hard_delete.py::TestHardDeleteConversation::test_hard_delete_removes_conversation_artifacts_and_records_event`
- Steps:
  - Verify hard delete action is restricted to `admin`.
  - Confirm conversation/messages/attachment binaries/metadata are removed.
  - Confirm minimal deletion event persists: `conversation_id`, actor, timestamp, optional reason.
  - Confirm no message contents or binaries remain after deletion.

## Rollout checklist
1. Apply DB migrations.
2. Set and validate `ATTACHMENTS_DIR`, `EXPORTS_DIR`, `EXPORTS_TTL_DAYS`.
3. Apply proxy config for internal redirect paths and restart proxy.
4. Enable feature flags in staging.
5. Execute A0-A7 checklist in staging with seeded agent/admin users (supervisor is legacy/out of scope).
6. Resolve failures and repeat checks.
7. Obtain stakeholder sign-off and change-window approval.
8. Roll out to production (feature flags initially ON only for allowed roles/teams if needed).
9. Run post-deploy smoke subset: A0, A1, A3, A6, A7.

## Rollback procedure
1. Disable Extras feature flags:
   - `FEATURE_ATTACHMENTS_ENABLED=false`
   - `FEATURE_EXPORTS_ENABLED=false`
   - `FEATURE_HARD_DELETE_ENABLED=false`
   - `FEATURE_TAXONOMY_ADMIN_ENABLED=false`
2. Revert app deployment to previous stable release if required.
3. Restore proxy config to previous known-good version if download/view failures are proxy-related.
4. Verify core messaging flows remain healthy (`CHATBOT`, `EN ESPERA`, `ASIGNADOS`, close/reassign).
5. Keep data artifacts intact unless a separate incident runbook explicitly requires cleanup.

## Operator/Admin short guide
### Agent
- Use the paperclip in composer to upload attachments.
- If upload is rejected, check file type and size before retry.
- Verify final send state in message history (`sent` or `failed`).
- Use conversation details to assign tags.

### Admin
- Manage taxonomy in admin UI (create/rename/archive).
- Use hard delete only when policy requires irreversible removal.
- Trigger exports for audit/support and verify expiry cleanup policy.
- Review proxy authorization failures/logs if view/download issues are reported.

## Sign-off record
- Staging validation owner:
- Product/ops approver:
- Date:
- Result: [ ] Approved [ ] Rejected

