---
name: implement-from-spec
description: Implement code strictly from docs/specs/<slug> (SPEC/PLAN/TASKS/ACCEPTANCE). Execute at most 1–2 atomic tasks per run, enforce spec-anchored discipline, 1 commit per task, and push per chunk. Maintain TASKS Execution status + CHECKPOINT.md for resumable work. Do not redesign or add scope.
---

# implement-from-spec (Codex CLI Orchestrator)

## Scope and intent
Execution-only. This skill exists to **implement** an already-approved contract, not to design it.

Paths are relative to the repo root.

**Contract files (source of truth):**
- `docs/specs/<slug>/SPEC.md`
- `docs/specs/<slug>/PLAN.md`
- `docs/specs/<slug>/TASKS.md`
- `docs/specs/<slug>/ACCEPTANCE.md`

## Inputs
Required:
- `<slug>` (spec identifier under `docs/specs/<slug>/`)

Optional scope:
- “Do the next task”
- “Do tasks T1.1 and T1.2”
- “Do Phase 0”

Default scope (if user does not specify):
- Use `Current task` from `TASKS.md` → `## Execution status`

## Hard stops (must enforce before any code changes)
Stop immediately and do not implement if any of the following is true:

0) `<slug>` is missing or ambiguous → **STOP** and ask for it (do not guess).
1) You are not on `impl/<slug>` OR you are in detached HEAD → **STOP** and fix Git state before any edits.
2) Any required contract file is missing under `docs/specs/<slug>/`.
3) `SPEC.md` has an **Open Questions** section and it is **not empty**.
4) `TASKS.md` is missing `## Execution status`, or `## Execution status` is **not the last section**, or it lacks:
   - `Status:`
   - `Current task:`
   - `Last updated:`
5) `Status: DONE` → do not implement new code.
   - Only run promotion workflow if the user asks to promote/merge OR `impl/<slug>` is ahead of `dev` (see `references/09-promotion-workflow.md`).

## Non-negotiable guardrails
- Implement **at most 1–2 tasks per run** (one chunk).
- Do **not** redesign, re-open decisions, add “bonus features”, or refactor unrelated code.
- If something is unclear after checking SPEC → TASK → PLAN: **STOP** (do not guess).
- If implementation requires a requirements change: **STOP**, update SPEC + TASKS + ACCEPTANCE + Changelog first, then continue.

## Mandatory reference read order (progressive disclosure)
Before implementing anything, you MUST read and follow these references:

1) `references/01-required-files-and-preconditions.md`
2) `references/04-hard-guardrails.md`
3) `references/06-git-discipline.md`

Then read the remaining references in order as needed:

- `references/00-purpose-and-inputs.md`
- `references/02-env-and-deps.md`
- `references/03-browser-verification-policy.md`
- `references/05-multi-agent-safety.md`
- `references/07-progress-accounting.md`
- `references/08-execution-workflow.md`
- `references/09-promotion-workflow.md`
- `references/10-failure-mode.md`

If any referenced rule conflicts with repo policy, **STOP** and surface the conflict.

## Optional helper scripts
These scripts are optional helpers. Run them only if the repo environment allows executing them safely.

- Contract check:
  - `python scripts/verify_contract.py <slug>`
- TASK progress (optional):
  - `python scripts/tasks_progress.py docs/specs/<slug>/TASKS.md`
- CHECKPOINT helper (best-effort):
  - `python scripts/checkpoint_from_tasks.py <slug>`

## Templates (optional helpers)
These are copy/paste templates (no templating engine required):
- `assets/templates/EXECUTION_STATUS_BLOCK.md.tpl`
- `assets/templates/CHECKPOINT.md.tpl`
- `assets/templates/COMMIT_MESSAGE.tpl`
- `assets/templates/PR_BODY_DEV.md.tpl`
- `assets/templates/PR_BODY_MAIN.md.tpl`

## Quick start checklist (must pass before coding)
1) Verify contract invariants (script or manual)
2) Select and validate scope: max 2 tasks; each task definition must be well-specified
3) Execute the chunk:
   - Implement → verify → commit per task → update `TASKS.md` + `CHECKPOINT.md` → docs commit → push

## Expected outputs every run (reporting discipline)
At the end of the chunk, report:
- Branch: `impl/<slug>`
- Tasks implemented (max 2) and done condition met (yes/no)
- Commits created (hash + message)
- Files changed (path + reason)
- Verification performed (and not performed, with reason)
- Updated `## Execution status` + CHECKPOINT summary
- Any deviations must link to SPEC Changelog entry

This skill values **discipline over creativity**.