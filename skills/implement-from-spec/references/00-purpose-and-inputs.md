# Purpose and inputs

## Purpose
Implement code **only** after the design has been finalized via `spec-interview`.

This skill is execution-only:
- SPEC is the contract (source of truth)
- PLAN is the strategy
- TASKS is the executable backlog (atomic units)
- ACCEPTANCE is the verification target
- Git history mirrors TASK execution (auditable + resumable)

## Inputs
Required:
- `<slug>` identifying the spec under `docs/specs/<slug>/`

Optional scope:
- next task / specific TaskIDs / a phase (if defined in TASKS)

Default scope:
- `Current task` from `TASKS.md` → `## Execution status`
