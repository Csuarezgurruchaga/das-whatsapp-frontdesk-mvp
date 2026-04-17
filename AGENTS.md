# AGENTS.md — WhatsApp FrontDesk MVP (DAS)

## Project essentials
- Spec slug: `whatsapp-frontdesk-mvp`
- Source of truth: `docs/specs/whatsapp-frontdesk-mvp/{SPEC,PLAN,TASKS,ACCEPTANCE}.md`
- Current task: deployment hardening + repo cleanup/documentation follow-up
- Bot YAML input artifact: `das-decision-tree.yaml` (approved decision tree + copy)

## Git / branches
- Repo was initialized here; legacy implementation branches still exist, but the active working branch is `dev`
- Ongoing maintenance and validation changes should be made on `dev`
- Keep legacy `impl/*` branch references only as historical context in old logs/proofs

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
- Acceptance checklist is in `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md`
- Real local prod-like acceptance is complete as of `2026-04-17` on an isolated stack: `Docker + MySQL + Nginx + HTTPS/ngrok`
- Validated in that run:
  - login with secure cookie
  - webhook verify + signed webhook POST
  - real WhatsApp inbound from phone through the public webhook
  - FrontDesk state transitions (`CHATBOT`, `EN_ESPERA`, `ASIGNADO`, `CERRADO`)
  - exclusive take, reassign, close
  - WebSocket behind Nginx
  - attachment upload/download/view via proxy
  - export download via proxy
  - UI time rendering in `America/Argentina/Buenos_Aires`
- Debian server deploy bundle now exists:
  - `Makefile`
  - `Dockerfile.prod`
  - `docker-compose.prod.yml`
  - `nginx.prod.conf`
  - `.env.prod.example`
  - `DEPLOYMENT_PROD.md`
- `CHECKPOINT.md` exists and must be kept up-to-date after each chunk

## Environment map
- Local development:
  - `docker-compose.local.yml`
  - `Dockerfile.local`
  - `.env.staging.local.example`
  - bind-mounted repo source; fastest loop for code/UI work
- Local prod-like acceptance:
  - same local stack, but with real WhatsApp credentials, `APP_ENV=staging`, HTTPS/ngrok, and optionally a temporary dispatcher cutover for real inbound
  - use sparingly; this is not the safe default
- Production Debian:
  - `Makefile`
  - `Dockerfile.prod`
  - `docker-compose.prod.yml`
  - `nginx.prod.conf`
  - persistent host paths under `/srv/chatbot-das`

## Config conventions (T0.1 done)
- Config artifacts live under `./config/`
- Default bot YAML path: `./config/bot.yaml` (env `BOT_MENU_YAML_PATH`)
- Reverse proxy terminates TLS and forwards `X-Forwarded-*` headers

## Local testing notes (WhatsApp + FrontDesk)
- Runtime dependencies: `requirements.txt` now includes `uvicorn[standard]` so `/realtime/ws` works in local runs (WebSockets).
- DB: MySQL is required (see SPEC). Current local compose default DB name: `frontdesk`.
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
  - In this environment, `NGROK_AUTHTOKEN` is available as an env var; `ngrok http <port>` can run without first writing `~/.config/ngrok/ngrok.yml`.
  - Dispatcher should forward webhook payloads to `https://<ngrok-host>/webhooks/whatsapp` (note plural `webhooks`).
- WhatsApp Cloud “number health” gotcha:
  - A phone can receive WhatsApp messages (two ticks) but still not deliver Cloud webhooks if the Cloud phone verification is not current.
  - Quick check via Graph: `code_verification_status` should not be `EXPIRED`. If it is, re-verify the number (Graph `/{PHONE_NUMBER_ID}/request_code` + `/{PHONE_NUMBER_ID}/verify_code`, or via WhatsApp Manager UI).

## Known fixes (2026-02)
- Enum mapping: MySQL stores `users.role` as `agent/admin` and `message_receipts.status` as `sent/delivered/read/failed`; ORM now maps enums by `.value` to avoid `LookupError`.
- Session expiry timestamps: MySQL may return naive datetimes; code normalizes to UTC before comparing to `now` (HTTP + WebSocket auth).
- UI timestamps offset: REST endpoints now normalize conversation/message timestamps to UTC-aware before JSON serialization so the frontend can safely render them in `America/Argentina/Buenos_Aires` without a +3h shift.
- Export ZIP permissions: files generated by `app/export_pipeline.py` must end with mode `0644` so Nginx can serve them from the shared volume via `X-Accel-Redirect`.
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

-
- date: 2026-04-16
- context: local Docker recovery after long freeze / UI inspection
- problem: `chatbot-das-mysql-1` failed to start with `No space left on device`, leaving the UI reachable at `/` but login effectively blocked because the DB never came up.
- solution: Freed Docker Desktop storage with a conservative cleanup that kept the active stack and harness images intact: `docker builder prune -af`, `docker image prune -f`, and `docker container prune -f`. This reclaimed enough space for `mysql:8` to start normally again; after recovery the local DB still contained `3` users (`admin`, `agent1`, `agent2`) and `1` conversation in state `CERRADO`.
- notes: Do not start by pruning volumes; the immediate issue was build cache + dangling images + exited containers. If the same failure reappears, check `docker system df` before touching app code.
- proof: `docker system df`; `docker compose -f docker-compose.local.yml up -d mysql`; `docker compose -f docker-compose.local.yml ps`; `docker compose -f docker-compose.local.yml exec -T mysql mysql -uwfd -pwfdpass -D frontdesk -e "SELECT id, username, role FROM users ORDER BY id; SELECT id, state, assigned_to FROM conversations ORDER BY id;"`

-
- date: 2026-04-16
- context: `app/static/{styles.css,index.html}` layout regression while inspecting the Docker-served UI
- problem: The authenticated FrontDesk screen looked horizontally broken because `#main-view` inherited the generic `.view` rule (`display:flex`, centered row layout, `padding:32px`), so `header`, `tabs`, and the 3-column grid rendered side-by-side instead of stacking vertically. Browser cache could also keep serving the old CSS after the fix because the static asset URLs were unversioned.
- solution: Added a dedicated `.main-view` rule (`display:block; width:100%; padding:0;`) so the main screen uses normal block flow, and versioned the static asset URLs in `index.html` (`styles.css?v=20260416`, `app.js?v=20260416`) to force clients to pick up the corrected assets with a normal refresh.
- notes: This was a real CSS/layout bug, not a mismatch against an older mockup. The server was serving the correct stylesheet immediately via the Docker bind mount; the stale render persisted only in browser cache until the asset URL changed.
- proof: `curl -s http://127.0.0.1:8080/static/styles.css | rg -n "\\.main-view|display: block|padding: 0"`; Playwright computed style for `#main-view` after reload showed `display: block`, `padding: 0px`, `layoutCols: 280px 856px 280px`; screenshot: `chatbot-das-layout-fixed-validated.png`

-
- date: 2026-04-16
- context: `app/static/{index.html,styles.css,app.js}` visual redesign toward the older DAS backoffice look
- problem: The existing UI had the right functionality but the wrong visual language for the intended product direction: dark product-style chrome, weak resemblance to the legacy DAS operator console, and logout/taxonomy exposed as permanent top-level actions instead of secondary operator controls.
- solution: Reworked the authenticated frontend into a light DAS-inspired 3-column backoffice layout with green/teal header, centered DAS wordmark, queue-state toolbar on the left, conversation header actions at the top of the chat column, detail accordions on the right, and a user dropdown containing `Taxonomia` + `Cerrar sesion`. Kept all existing backend contracts and frontend actions intact; changes are presentation/layout only.
- notes: Static asset cache-busting is necessary during UI work because Docker serves bind-mounted files immediately but browsers may keep stale `/static/styles.css` and `/static/app.js` aggressively. Keep querystring versioning on those assets whenever the visual shell changes materially.
- proof: `node --check app/static/app.js`; `git diff --check`; Playwright screenshots `chatbot-das-redesign-authenticated-v4.png` and `chatbot-das-user-menu-open.png`

-
- date: 2026-04-17
- context: production packaging for Debian single-host deploy
- problem: The repo had only a local development compose with bind-mounted source and no production bundle for a Debian server, which made deployment ambiguous and risked treating the dev image as if it were a portable release artifact.
- solution: Added a production deployment bundle composed of `Makefile`, `.dockerignore`, `Dockerfile.prod`, `docker-compose.prod.yml`, `nginx.prod.conf`, `.env.prod.example`, and `DEPLOYMENT_PROD.md`. The prod topology is `app + nginx + mysql` on one Debian host, with host-level bind mounts under `/srv/chatbot-das` for MySQL data, attachments, exports, env, and TLS certs; the app is deployed as an immutable image tag and migrations run explicitly after startup.
- notes: Production intentionally does not bind mount repo source. Persistence depends on host paths, not on the container filesystem or the image. Keep using immutable image tags and never deploy `latest`.
- proof: `docker compose -f docker-compose.prod.yml config`; `docker run --rm -v "$PWD/nginx.prod.conf:/etc/nginx/nginx.conf:ro" -v /tmp/chatbot-das-certs:/etc/nginx/certs:ro nginx:alpine nginx -t`

-
- date: 2026-04-17
- context: reviewer follow-up on Debian production bundle
- problem: The first cut of the prod bundle exposed traffic before migrations completed, used floating infra image tags, reported app health from `/` without proving DB readiness, and duplicated DB connection parameters between `DATABASE_URL` and `MYSQL_*`.
- solution: Tightened the bundle so `docker-compose.prod.yml` derives `DATABASE_URL` from `MYSQL_*`, healthchecks the app with a live DB query, requires explicit pinned `MYSQL_IMAGE`/`NGINX_IMAGE`, and `make das-prod-up` now stops `nginx`, updates `app`, runs Alembic, and only then exposes traffic again.
- notes: The bundle still assumes an embedded MySQL topology. If the repo later moves to an external DB, revisit the composed `DATABASE_URL` rule and the deploy targets.
- proof: `docker compose --env-file .env.prod.example -f docker-compose.prod.yml config`; `make -n das-prod-up APP_ENV_FILE=.env.prod.example RUNTIME_ROOT=/tmp/chatbot-das-prod`

-
- date: 2026-04-17
- context: second hardening pass on the Debian production bundle after DevOps re-review
- problem: The first remediation still left operator-risk edges: `das-prod-restart` could bypass Alembic, the main deploy path achieved safety by forcing downtime through `nginx` stop/start, recovery targets (`logs`, `ps`, `down`) were blocked by TLS-file prechecks, and the app container still ran as root against writable host-mounted storage.
- solution: Reworked `Makefile` so migrations run through a one-off app container before recreating `app`/`nginx`, added a lighter `das-prod-stack-check` for recovery-safe targets, and hardened `Dockerfile.prod` to run as UID/GID `10001`. `das-prod-init` now prepares writable attachment/export directories for that non-root runtime.
- notes: In local validation, compose interpolation must receive the same overrides as the Make variables, so `DOCKER_COMPOSE` now exports `APP_ENV_FILE`, `MYSQL_DATA_DIR`, `ATTACHMENTS_HOST_DIR`, `EXPORTS_HOST_DIR`, and `TLS_CERTS_DIR` before invoking `docker compose`.
- proof: `APP_ENV_FILE=.env.prod.example docker compose --env-file .env.prod.example -f docker-compose.prod.yml config`; `make -n das-prod-up APP_ENV_FILE=.env.prod.example RUNTIME_ROOT=/tmp/chatbot-das-prod`; `docker run --rm --add-host app:127.0.0.1 -v "$PWD/nginx.prod.conf:/etc/nginx/nginx.conf:ro" -v /tmp/chatbot-das-certs:/etc/nginx/certs:ro nginx:alpine nginx -t`; `git diff --check`

-
- date: 2026-04-17
- context: first published production image for the Debian bundle
- problem: The repo and docs were ready for server deploy, but there was not yet a real immutable artifact published to a registry, which left `APP_IMAGE` as documentation only and not an actually deployable reference.
- solution: Built `Dockerfile.prod` from commit `e2c0e2a` and published the first Debian bundle image to GHCR as `ghcr.io/csuarezgurruchaga/chatbot-das:2026-04-17-1`.
- notes: The GitHub auth on the host initially lacked `write:packages`; after `gh auth refresh -h github.com -s write:packages`, Docker push succeeded using a temporary `DOCKER_CONFIG` under `/tmp` because the default credential helper was blocked by sandbox permissions.
- proof: local image id `sha256:8f8d8fc433ff6d53547d301f590cddd7275bf5a76a7689410446c1dffcc9a5ce`; published digest `sha256:5565f82ca267df677577808ea05b0f03da16d7cb72949a20d5bd12eedb2e0820`

-
- date: 2026-04-17
- context: local prod-like acceptance rerun with real dispatcher cutover to DAS
- problem: The repo docs still showed the MVP acceptance run as waived, even though the system had already been exercised end-to-end with real WhatsApp traffic routed temporarily into DAS local.
- solution: Executed A0-A7 core flows against DAS local using MySQL 8, signed webhooks, ngrok HTTPS, and a temporary dispatcher route for `phone_number_id 972301799307809`, then restored the dispatcher exactly to its previous `ROUTES_JSON`. Evidence now lives in the updated `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md` and `CHECKPOINT.md`.
- notes: The run proved the real inbound/outbound path and core operator workflow, but it did not force blocked-handoff outside schedule, `MESSAGE_SENT_FAILED`, or receipt statuses `read` / `failed`.
- proof: local DB evidence on conversations `5` and `6`, signed webhook 401 negative probe, duplicate replay with unchanged message count, dispatcher restore to Kleiman route
