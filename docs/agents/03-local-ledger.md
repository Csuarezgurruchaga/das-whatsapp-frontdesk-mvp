# Local `AGENTS.md` ledger (project-specific)

## Global vs local
- `$HOME/.codex/AGENTS.md` is GLOBAL policy (repo-independent rule set).
- `<repo_root>/AGENTS.md` is LOCAL and project-specific:
  - high-signal, append-only project log
  - survives context resets, agent restarts, squash merges

## Creation rule
When starting work in a repo:
- If `<repo_root>/AGENTS.md` is missing: create it by copying a template verbatim.
  - Preferred (user-level template): `cp "$HOME/.codex/templates/agents_local.md" "<repo_root>/AGENTS.md"`
  - Fallback (repo template): `cp "docs/agents/templates/local_template.md" "<repo_root>/AGENTS.md"`
- If both templates exist: keep them identical; update the repo template first.
- If it exists: read it before changes.

## Update rules (local ledger)
- Append-only by default.
- Do not rewrite/delete entries unless explicitly instructed.
- Avoid noise: log only what helps resume work after context loss.

## Triggers (when to log)
Log when:
- a bug is fixed (especially if a repro/test was added)
- a non-trivial design/architecture decision is made
- environment/infra/tooling changes were required to make progress
- a pitfall is discovered that could waste time again
