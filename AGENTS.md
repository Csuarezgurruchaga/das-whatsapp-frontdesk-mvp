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
