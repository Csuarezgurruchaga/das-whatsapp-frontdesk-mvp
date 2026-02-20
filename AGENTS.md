# AGENTS.md (GLOBAL)

Path: $HOME/.codex/AGENTS.md (GLOBAL). Project ledger: <repo_root>/AGENTS.md (LOCAL).

This file defines GLOBAL workflow and safety rules for coding agents.

Progressive disclosure: this file is intentionally short. Details live in `docs/agents/`.

## Quick start
- Ensure local ledger exists at `<repo_root>/AGENTS.md` (create it if missing).
- Classify scope (trivial vs non-trivial). If unsure: treat as non-trivial.
- Non-trivial: run `spec-interview` and create/update `<repo_root>/docs/specs/<slug>/SPEC.md` until it has zero Open Questions.

## Index
- Hard rules (non-negotiable): `docs/agents/00-hard-rules.md`
- Workflow (spec-first for non-trivial): `docs/agents/01-workflow.md`
- Verification & safety (tests, commands, bugfix repro): `docs/agents/02-verification-safety.md`
- Local `AGENTS.md` ledger (project log): `docs/agents/03-local-ledger.md`
- Tools (MCP servers: Context7 / Playwright / GCP): `docs/agents/04-tools-mcp.md`
- Merge philosophy (no CI yet): `docs/agents/05-merge-throughput.md`
