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
