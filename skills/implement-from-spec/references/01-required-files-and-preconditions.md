# Required files and preconditions

## Required directory
- `docs/specs/<slug>/`

## Required contract files (must exist)
- `SPEC.md`
- `PLAN.md`
- `TASKS.md`
- `ACCEPTANCE.md`

## Must create/maintain
- `CHECKPOINT.md`

If any required file is missing:
- STOP immediately.
- Explain what is missing.
- Recommend returning to `spec-interview`.
- Do NOT implement anything.

## STOP protocol (mandatory)
When a STOP condition is hit:
- Do NOT change code.
- Do NOT stage/commit/push anything.
- Report the exact failing condition and the minimal action required to resolve it.

If you already made changes before discovering the STOP:
- Report it.
- Revert them (or clearly instruct the user how).
- Do NOT continue implementation in the same run.

## Preconditions (hard)
Before writing code, verify:

1) `SPEC.md` contains an "Open Questions" section AND it is empty  
   - If not empty: STOP → return to `spec-interview`.

2) `SPEC.md` contains the spec-anchored statement (verbatim):

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

3) `TASKS.md` contains `## Execution status` as the LAST section  
   - If missing/malformed: STOP → return to `spec-interview`.

4) `TASKS.md` `## Execution status` includes:
   - `Status:`
   - `Current task:`
   - `Last updated:`

If `Status: DONE`:
- Do NOT implement new code.
- Follow promotion workflow only if the user requests it OR `impl/<slug>` is ahead of `dev` (see `references/09-promotion-workflow.md`).
- Then STOP.

## Optional helper
If the repo environment allows it, you may run:
- `python scripts/verify_contract.py <slug>`
If it fails: treat as STOP and report why.
