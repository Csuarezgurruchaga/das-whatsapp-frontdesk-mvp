# DEPLOYMENT — WhatsApp FrontDesk Extensions

## Acceptance run checklist

Last updated: 2026-02-06

### Scope
- Validate `docs/specs/whatsapp-frontdesk-extensions/ACCEPTANCE.md` criteria A0-A7.
- Execute in both local and staging/on-prem environments.

### Prereqs
- App is running with DB migrated.
- Roles are seeded for `operator`, `admin`, and `supervisor`.
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
- Local: PARTIAL (backend/unit verifications available; full browser + proxy + SSO checks require integrated runtime)
- Staging/on-prem: PENDING (required for final sign-off)

### Local baseline verification (automated)
- `.venv/bin/python -m unittest discover -s tests -v`
- `node --check app/static/app.js`

### Checklist template (run per environment)
#### A0 - Browser smoke (web)
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Open `/` in Chromium.
  - Confirm no critical console errors.
  - Run the primary happy path end-to-end.

#### A1 - Attachments upload/validation/send/status
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Upload valid files from composer (paperclip) for image, audio/video, and document classes.
  - Confirm blocked uploads for invalid MIME and oversize constraints (100MB max + per-type caps).
  - Confirm MIME extension fallback applies only when browser MIME is empty/octet-stream.
  - Confirm status transitions `uploading -> sent/failed` and persisted final state.

#### A2 - Attachments history rendering
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Confirm history bubble renders attachment icon, filename, size, and status.
  - Confirm failed sends remain visible with failure status.

#### A3 - Reverse-proxy view/download authorization
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - From an authorized session, confirm `View` works for PDF/PNG/JPG/JPEG/TXT and `Download` works for all supported types.
  - Confirm unauthorized user gets access denied on attachment/export authorization endpoints.
  - Confirm backend uses internal redirect response headers (no backend file streaming).

#### A4 - Tipification tags in conversation details
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - Assign multiple tags to a conversation and confirm persistence on refresh.
  - Confirm tags are visible in conversation details.
  - Confirm close-conversation flow does not require tags.

#### A5 - Taxonomy admin role/lifecycle checks
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - As `admin`, create, rename, and archive/disable tags.
  - As `supervisor`, verify taxonomy admin is visible but read-only.
  - Confirm rename migrates existing conversation tag references.

#### A6 - Export ZIP generation/permissions/retention
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
- Steps:
  - As `admin` and `supervisor`, request export for a conversation.
  - Verify ZIP contains JSON transcript and expected attachments.
  - Confirm export download is authorized and served through reverse-proxy path.
  - Validate retention behavior with `EXPORTS_TTL_DAYS` (dry-run first, then real cleanup in non-prod).

#### A7 - Hard delete and minimal deletion audit
- Status: [ ] PASS [ ] FAIL [ ] WAIVED (reason)
- Evidence/notes:
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
5. Execute A0-A7 checklist in staging with seeded operator/admin/supervisor users.
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
### Operator
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
