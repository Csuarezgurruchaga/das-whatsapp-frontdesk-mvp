# Workflow (GLOBAL)

## Trivial vs non-trivial

### Trivial / mechanical changes (MAY skip spec workflow)
All must be true:
- single-file edit
- <20 lines changed
- no architecture impact

Examples:
- typo fixes, formatting, linting
- patch-level dependency bumps
- log message improvements

### Non-trivial changes (MUST use spec workflow)
Any of:
- affects >2 files OR >50 lines total
- changes public APIs, data models, or schemas
- introduces new dependencies or architectural patterns
- modifies authentication/authorization/security logic
- changes behavior relied upon by users/external systems

**When in doubt:** treat as non-trivial.

## Spec workflow
1) Run `spec-interview` first.
2) Create/update `docs/specs/<slug>/SPEC.md`.
3) Ensure SPEC has **zero Open Questions**.
4) Implement minimal, reviewable diffs.
5) Verify (see `02-verification-safety.md`).
6) Propose a local ledger entry (see `03-local-ledger.md`) when triggers apply.

## Implementation principles
- Prefer minimal diffs; avoid unrelated refactors.
- Follow existing project conventions (README/Makefile/pyproject/etc.).
- Primary language: Python. Use per-project `.venv`. Never install deps globally.
