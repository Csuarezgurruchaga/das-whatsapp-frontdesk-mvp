# Hard rules (GLOBAL)

These rules must be followed in every repository.

## 1) Pre-flight (before any code changes)
- **Local `AGENTS.md` must exist at `<repo_root>/AGENTS.md`.**
  - If missing: create it (see `03-local-ledger.md`).
  - Action: read it fully before proceeding.
- **Understand scope** (trivial vs non-trivial). If uncertain: treat as non-trivial.
- **Check for existing specs** under `<repo_root>/docs/specs/` (if present).

## 2) Spec-first gates
- **Non-trivial work MUST use the spec workflow** (see `01-workflow.md`).
- **No implementation until the SPEC has zero Open Questions.**

## 3) No destructive commands without permission
If a command could **modify/delete** files or resources, ask first.

Destructive includes (examples): `rm`, `mv` (overwrite), `git reset --hard`, `git clean -fd`, cloud `delete/disable/traffic shifts`.

## 4) No dependency / API / schema changes without permission
Ask before:
- adding dependencies or tools
- changing public APIs
- changing data models or schemas
- changing auth/authz/security behavior

## 5) Multi-agent safety
- Do not overwrite or disrupt other agents' work.
- Only the primary/orchestrator agent integrates changes.
- Subagents must include: (a) repro location, (b) failing condition pre-fix, (c) proof commands.

## 6) No assumption policy
If something is ambiguous, ask. Provide 2–3 options with trade-offs + a recommendation.
