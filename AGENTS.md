# AGENTS.md — WhatsApp FrontDesk MVP (DAS)

## Project essentials
- Spec slug: `whatsapp-frontdesk-mvp`
- Source of truth: `docs/specs/whatsapp-frontdesk-mvp/{SPEC,PLAN,TASKS,ACCEPTANCE}.md`
- Current task: N/A (all tasks complete; acceptance run still needs execution in real envs)
- Bot YAML input artifact: `das-decision-tree.yaml` (approved decision tree + copy)

## Git / branches
- Repo was initialized here; branches exist: `main`, `dev`, `impl/whatsapp-frontdesk-mvp`
- Work must happen on `impl/whatsapp-frontdesk-mvp` per spec discipline
- Last commits already pushed on `impl/whatsapp-frontdesk-mvp`

## Push/auth gotchas
- Global git config rewrites `https://github.com/` to SSH:
  - `url.git@github.com:.insteadof https://github.com/`
- SSH to GitHub is blocked in this environment, so pushing must use HTTPS and bypass global config:
  - Use `GIT_CONFIG_GLOBAL=/dev/null`
  - Use `GIT_ASKPASS` with a token (often available as env `GITHUB_PERSONAL_ACCESS_TOKEN` in Codex; otherwise from `~/.codex/config.toml` under an `env` section)

## Untracked files to avoid committing
- `.DS_Store` files
- `PRD.md`, `UI-adjunto.png`, `das-decision-tree.yaml`
- `docs/specs/whatsapp-frontdesk-extensions/` (out of scope for MVP)

## Execution status reminders
- `TASKS.md` Execution status updated to `DONE`, `Progress: 13/13`
- Acceptance checklist is in `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md`; execute in local + staging/on-prem when env access is available
- `CHECKPOINT.md` exists and must be kept up-to-date after each chunk

## Config conventions (T0.1 done)
- Config artifacts live under `./config/`
- Default bot YAML path: `./config/bot.yaml` (env `BOT_MENU_YAML_PATH`)
- Reverse proxy terminates TLS and forwards `X-Forwarded-*` headers

## Local testing notes (WhatsApp + FrontDesk)
- Runtime dependencies: `requirements.txt` now includes `uvicorn[standard]` so `/realtime/ws` works in local runs (WebSockets).
- DB: MySQL is required (see SPEC). Typical local DB name: `chatbot_mvp`.
- Migrations: run `alembic upgrade head` after setting `DATABASE_URL`.
- Users: there is no “create user” API; seed at least `2` agents + `1` admin in table `users` to log into `/`.
  - Password hashing helper: `app.security.hash_password()`.
- Minimal local env vars:
  - `APP_ENV=development` (easiest for local testing; webhook signature is not required).
  - `DATABASE_URL` (SQLAlchemy URL, using PyMySQL).
  - `SESSION_SECRET` (required for sessions).
  - `BOT_MENU_YAML_PATH` (optional; defaults to `./config/bot.yaml`).
- WhatsApp end-to-end requires outbound credentials:
  - `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`.
  - If running `APP_ENV=staging|production`, also set: `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`.
- Ngrok testing pattern (optional):
  - Run locally on a fixed port (e.g. `8010`) and expose via `ngrok http <port>`.
  - Dispatcher should forward webhook payloads to `https://<ngrok-host>/webhooks/whatsapp` (note plural `webhooks`).
- WhatsApp Cloud “number health” gotcha:
  - A phone can receive WhatsApp messages (two ticks) but still not deliver Cloud webhooks if the Cloud phone verification is not current.
  - Quick check via Graph: `code_verification_status` should not be `EXPIRED`. If it is, re-verify the number (Graph `/{PHONE_NUMBER_ID}/request_code` + `/{PHONE_NUMBER_ID}/verify_code`, or via WhatsApp Manager UI).

## Known fixes (2026-02)
- Enum mapping: MySQL stores `users.role` as `agent/admin` and `message_receipts.status` as `sent/delivered/read/failed`; ORM now maps enums by `.value` to avoid `LookupError`.
- Session expiry timestamps: MySQL may return naive datetimes; code normalizes to UTC before comparing to `now` (HTTP + WebSocket auth).
- UI timestamps offset: REST endpoints now normalize conversation/message timestamps to UTC-aware before JSON serialization so the frontend can safely render them in `America/Argentina/Buenos_Aires` without a +3h shift.
## 2026-02-06 Development log

- date: 2026-02-06
- context: `docs/specs/whatsapp-frontdesk-extensions` + `app/config.py` (Task `T0.1`)
- problem: Extras spec required explicit baseline for env vars, role semantics, and feature flags before backend/UI tasks, but Core only had partial runtime config and only `agent/admin` roles.
- solution: Added Extras runtime config scaffold in `app/config.py` (`ATTACHMENTS_DIR`, `EXPORTS_DIR`, `EXPORTS_TTL_DAYS`, and four `FEATURE_*` toggles), documented role/config/flag matrix in `docs/specs/whatsapp-frontdesk-extensions/CONFIG.md`, and advanced spec execution tracking (`TASKS.md` + new `CHECKPOINT.md`).
- notes: `supervisor` remains a planned role to introduce in later Extras tasks; current Core role mapping is preserved for now (`operator -> agent`).
- proof: `python3 -c "from app.config import get_extras_config; print(get_extras_config())"`

- date: 2026-02-06
- context: `app/db/models.py`, `app/db/crud.py`, `alembic/versions/20260206_01_add_attachment_metadata_table.py` (Task `T1.1`)
- problem: Extras required attachment metadata persistence (schema + CRUD) with stable retry semantics by `attachment_id` and query by `conversation_id`.
- solution: Added `AttachmentMetadata` model and `AttachmentStatus` enum, created Alembic migration with required FKs/constraints/indexes, and implemented CRUD helpers including idempotent `get_or_create_attachment_metadata`.
- notes: Full `alembic upgrade head` against SQLite fails due pre-existing revision `20260202_03` using unsupported `ALTER COLUMN ... DROP NOT NULL`; validated T1.1 behavior with isolated SQLAlchemy roundtrip instead.
- proof: `.venv/bin/python - <<'PY' ... T1.1 CRUD roundtrip OK ... PY`

- date: 2026-02-06
- context: `git` operaciones remotas (fetch/pull/push) en este entorno
- problem: La comunicación remota por SSH hacia GitHub está bloqueada y además se pidió explícitamente evitar SSH para `git`.
- solution: Establecer como regla de trabajo usar siempre HTTP/HTTPS para `git` con red (sin SSH), incluyendo push del branch activo por URL `https://github.com/...`.
- notes: Mantener `GIT_CONFIG_GLOBAL=/dev/null` cuando sea necesario para evitar rewrite global `https -> ssh`; usar `GIT_ASKPASS` + token para autenticación no interactiva.
- proof: `git push https://github.com/Csuarezgurruchaga/das-whatsapp-frontdesk-mvp.git impl/whatsapp-frontdesk-extensions`

- date: 2026-02-06
- context: `app/export_cleanup.py`, `tests/test_export_cleanup.py`, `docs/specs/whatsapp-frontdesk-extensions/{TASKS.md,CHECKPOINT.md}` (Task `T1.6`)
- problem: Extras required deterministic export retention cleanup by `EXPORTS_TTL_DAYS` with low risk of deleting unrelated files and with a safe staging validation mode.
- solution: Added TTL cleanup module that uses ZIP mtime as timestamp source, deletes only files that match the export naming convention, removes empty per-conversation export directories, and provides dry-run execution via `python -m app.export_cleanup --dry-run`.
- notes: Cleanup intentionally skips non-export ZIP files to reduce accidental deletions from `EXPORTS_DIR`.
- proof: `.venv/bin/python -m unittest -v tests/test_export_cleanup.py`

- date: 2026-02-06
- context: `app/hard_delete.py`, `app/api/conversations.py`, `app/db/{models.py,crud.py}`, `alembic/versions/20260206_02_add_conversation_deletion_events_table.py`, `tests/test_hard_delete.py` (Task `T1.7`)
- problem: Extras required an admin-only hard delete flow that removes conversation artifacts (DB + filesystem) and still preserves a minimal deletion audit record after the conversation row is gone.
- solution: Implemented `hard_delete_conversation` service + admin API endpoint, added DB cleanup ordering for dependent tables, file cleanup for attachments/exports, and introduced `conversation_deletion_events` (no FK to conversations) to persist `conversation_id`, actor, timestamp, and optional reason after hard delete.
- notes: Added SQLite-only ID fallback in `create_conversation_deletion_event` to keep deterministic tests working with the existing BigInteger PK pattern.
- proof: `.venv/bin/python -m unittest -v tests/test_hard_delete.py`

- date: 2026-02-06
- context: `app/api/conversations.py`, `docs/specs/whatsapp-frontdesk-extensions/PROXY.md`, `tests/test_proxy_download_authorization.py` (Task `T2.1`)
- problem: Extras required backend-authorized attachment/export downloads via reverse-proxy (`X-Accel-Redirect`) without backend streaming, but there were no authorization endpoints nor proxy contract docs.
- solution: Added attachment download/view + export download authorization endpoints that validate session/permissions and emit `X-Accel-Redirect` with safe relpaths and content headers; documented Nginx mapping requirements; added endpoint-level tests for success and authorization failures.
- notes: Test coverage was implemented as direct endpoint function tests because `httpx` is not installed in this environment (`fastapi.testclient` unavailable).
- proof: `.venv/bin/python -m unittest discover -s tests -v`

- date: 2026-02-06
- context: `app/static/{index.html,styles.css,app.js}`, `docs/specs/whatsapp-frontdesk-extensions/{TASKS.md,CHECKPOINT.md}` (Task `T2.2`)
- problem: Frontend attachments implementation was interrupted mid-session, leaving partial wiring (`attach` input/modal handlers not bound) and a CSS precedence bug where the preview modal could remain visible despite `hidden`.
- solution: Completed the attachments UI flow end-to-end (paperclip trigger, upload request, optimistic `uploading`, final `sent/failed`, history bubble rendering, view/download actions), fixed modal hidden-state override (`.attachment-modal.hidden`), and updated spec execution status/checkpoint to move next to `T2.3`.
- notes: Browser smoke for T2.2 still requires seeded/authenticated runtime environment; backend regression suite remained green.
- proof: `node --check app/static/app.js && .venv/bin/python -m unittest discover -s tests -v`

- date: 2026-02-06
- context: `app/{api/conversations.py,api/deps.py,db/models.py,db/crud.py,static/{index.html,app.js,styles.css}}`, `alembic/versions/20260206_03_add_taxonomy_and_conversation_tags.py`, `tests/test_taxonomy_and_tags.py` (Task `T2.3`)
- problem: Extras required conversation tipification and taxonomy admin UX with role gating (`admin` edit, `supervisor` read-only), but the codebase had no tag/taxonomy persistence, no APIs, and no frontend controls for tagging/taxonomy management.
- solution: Added taxonomy/tag schema + CRUD + API endpoints (list/create/update taxonomy and set conversation tags), extended conversation detail payload with assigned/available tags, introduced supervisor-aware role behavior for taxonomy paths, implemented detail-panel tag selection and taxonomy modal UI, and added deterministic endpoint-level tests.
- notes: Browser-level validation still requires authenticated seeded roles in a real runtime environment; backend regression suite remains green in unit-test mode.
- proof: `.venv/bin/python -m unittest -v tests/test_taxonomy_and_tags.py && .venv/bin/python -m unittest discover -s tests -v && node --check app/static/app.js`

- date: 2026-02-06
- context: `git` remoto (fetch/pull/push) para este repo en este entorno
- problem: Debe evitarse SSH y estandarizar credenciales no interactivas para futuras sesiones.
- solution: Regla operativa confirmada: usar siempre URL `https://github.com/...` para git con red y autenticación por `GIT_ASKPASS` con token desde variable de entorno `GITHUB_PRIVATE_ACCESS_TOKEN` (no usar `GITHUB_PERSONAL_ACCESS_TOKEN` para este flujo).
- notes: Mantener `GIT_CONFIG_GLOBAL=/dev/null` para evitar rewrite global `https -> ssh`.
- proof: `GIT_CONFIG_GLOBAL=/dev/null GIT_ASKPASS=/tmp/git-askpass.sh GITHUB_TOKEN=$GITHUB_PRIVATE_ACCESS_TOKEN git push https://github.com/Csuarezgurruchaga/das-whatsapp-frontdesk-mvp.git impl/whatsapp-frontdesk-extensions`

- date: 2026-02-06
- context: `app/{attachment_pipeline.py,api/conversations.py,static/app.js}` + `tests/{test_attachment_pipeline.py,test_proxy_download_authorization.py}` (Task `T3.1`)
- problem: Extras needed explicit observability for attachment send outcomes and proxy authorization/missing-file failures, plus clearer operator-facing errors for send failures.
- solution: Added attachment send success/failure counters and structured logs, added proxy auth-denial + missing-file logs in download authorization endpoints, and surfaced backend send-failure details in composer UI for text/attachment sends.
- notes: Metrics are in-process counters intended for task-level instrumentation; they reset on process restart and are validated in unit tests.
- proof: `.venv/bin/python -m unittest -v tests/test_attachment_pipeline.py tests/test_proxy_download_authorization.py && node --check app/static/app.js && .venv/bin/python -m unittest discover -s tests -v`

- date: 2026-02-06
- context: `docs/specs/whatsapp-frontdesk-extensions/{DEPLOYMENT.md,TASKS.md,CHECKPOINT.md}` (Task `T4.1`)
- problem: Release phase lacked an Extras-specific execution artifact for staged acceptance, rollback, and role-oriented operational guidance; final sign-off requirements were not anchored in a reusable checklist.
- solution: Added `DEPLOYMENT.md` with A0-A7 acceptance template, rollout checklist, rollback steps, and operator/admin short guide; updated execution status/checkpoint to reflect T4.1 is in progress pending staging/on-prem run and stakeholder approval.
- notes: Deterministic local checks remain available, but final task completion still requires integrated environment (NAS + proxy + SSO + seeded roles + WhatsApp credentials).
- proof: `.venv/bin/python -m unittest discover -s tests -v && node --check app/static/app.js`

- date: 2026-02-09
- context: `docs/specs/whatsapp-frontdesk-extensions/{SPEC.md,ACCEPTANCE.md,DEPLOYMENT.md}` (local acceptance alignment)
- problem: Local validation was running under a two-role operational scope (`agent`, `admin`), but spec/deployment acceptance text still required `supervisor` checks, creating false failures in A5/A6.
- solution: Updated Extras spec + acceptance + deployment checklists to reflect current operational scope (`agent`/`admin`): taxonomy admin remains `admin` only, export permission/verification is `admin` with explicit `agent` denial checks.
- notes: Repository code still contains `UserRole.SUPERVISOR` and related paths/tests; the documentation update only aligns current validation scope and does not remove supervisor support from code.
- proof: `rg -n "supervisor|admin \\+ supervisor" docs/specs/whatsapp-frontdesk-extensions/{SPEC.md,ACCEPTANCE.md,DEPLOYMENT.md}`

-
- date: 2026-02-10
- context: production deployment (Debian) planning
- problem: After completing the local "prod-like" acceptance run (Docker Desktop + ngrok + real WhatsApp webhook + Nginx X-Accel-Redirect), we want a reproducible production deploy flow on a Debian server, but key environment decisions are still pending.
- solution: Logged open questions and the target deploy deliverables to prepare once the acceptance run passes.
- open_questions:
  - DB: Will MySQL run on the same Debian host (container) or is there an external/managed MySQL already?
  - Storage: Where do `ATTACHMENTS_DIR` and `EXPORTS_DIR` live in prod (local disk vs NAS), and what are the exact mount paths?
  - TLS: Where is TLS terminated (on-host Nginx/Let's Encrypt vs upstream LB/proxy), and what is the public domain?
- target_deliverables (post-acceptance):
  - `docker-compose.prod.yml` using an immutable app image tag, env/secrets outside git, and persistent volumes/mounts for DB and storage.
  - `nginx.prod.conf` (TLS + WS upgrades + reverse proxy headers + X-Accel-Redirect internal locations).
  - `DEPLOYMENT_PROD.md` runbook: deploy, migrate, rollback, backups, and webhook troubleshooting.
- notes:
  - Preferred approach: build/push a versioned app image (CI), deploy via `docker compose pull && up -d`, run `alembic upgrade head` as a one-shot step, keep state out of the image.
  - Must preserve `Secure` cookies and signature enforcement: prod requires HTTPS and correct `X-Forwarded-*` headers.

-
- date: 2026-02-10
- context: local prod-like compose (MySQL 8 + PyMySQL + Alembic)
- problem: `alembic upgrade head` failed with `RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password auth methods` when connecting to MySQL 8 using PyMySQL (default auth plugin is commonly `caching_sha2_password`).
- solution: Added `cryptography` to `requirements.txt` so the `app` container can authenticate to MySQL 8 and run migrations.
- proof: Rebuild `app` image and re-run `docker compose -f docker-compose.local.yml exec app alembic upgrade head` (should connect and apply migrations).

-
- date: 2026-02-10
- context: local prod-like acceptance (handoff schedule)
- problem: Acceptance run requires validating `EN_ESPERA`/handoff flows, but the production handoff window (Mon-Fri 09:00-18:00 America/Argentina/Buenos_Aires) can block testing outside business hours.
- solution: Temporarily widened `handoff_schedule` in `config/bot.yaml` to `00:00-23:59` for the local acceptance run, with a plan to revert after finishing A0-A7.
- proof: Call `POST /bot/reload` as admin and verify selecting option `6` transitions the conversation to `EN_ESPERA`.

-
- date: 2026-02-11
- context: local prod-like acceptance (MySQL enum + exports/attachments)
- problem: Export generation failed in MySQL with `LookupError: 'sent' is not among the defined enum values` due to an enum mapping mismatch for `attachment_status`.
- solution: Updated `AttachmentMetadata.status` enum mapping to use `.value` strings (`uploading/sent/failed`) and added a regression unit test.
- proof: `docker compose -f docker-compose.local.yml exec app python -c "... generate_conversation_export_zip(...)"` succeeds; `python -m unittest -v tests/test_enum_mappings.py`
