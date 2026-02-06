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
  - Use `GIT_ASKPASS` with token from `~/.codex/config.toml` (`mcp_servers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN`)

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
