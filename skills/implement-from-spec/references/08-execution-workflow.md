# Execution workflow

## Step 0 — Hard gate: contract preconditions
Before any edits, ensure contract preconditions pass (see `references/01-required-files-and-preconditions.md`).
If any precondition fails: STOP (no code changes).
If a STOP is triggered after changes were made, revert them (or instruct how) and do not continue in the same run.

## Step 1 — Load and summarize contract
Read:
- `SPEC.md`
- `PLAN.md`
- `TASKS.md`
- `ACCEPTANCE.md`

Then summarize (5–8 bullets):
- What must be built
- What must NOT be built
- Key constraints
- Current execution status
- Which task(s) you will implement (max 2)

Task selection priority:
1) User-requested tasks (if explicit and valid)
2) Otherwise `Current task` from Execution status

## Step 2 — Ensure correct branch
Switch/create `impl/<slug>` using Git discipline (see `references/06-git-discipline.md`).

## Step 3 — Validate task scope (hard)
Hard limit: implement at most 1–2 tasks per run. If a task implies large diffs, STOP and recommend splitting TASKS.
For each chosen task (max 2), verify it is well-defined:
- Goal
- Inputs
- Outputs
- Steps
- Done condition
- Depends on (must be bracketed list like `[]` or `[T0.1, T1.2]`)
- Risks
- Test/Verification

If any missing/ambiguous:
- STOP and recommend returning to `spec-interview`.

## Step 4 — Implement
Implement only what is required for the chosen task(s).
Touch only files implied by the tasks. Keep diffs minimal.

### If necessary deviation is discovered
If implementation forces a change to requirements:
- STOP immediately (no partial hacks)
- Propose SPEC update (exact change, why, impact)
- Update SPEC/TASKS/ACCEPTANCE + SPEC Changelog first
- Continue only after docs are consistent

Changelog entry format:
- YYYY-MM-DD — <change summary>
  - reason: <why>
  - impact: <docs updated>

## Step 5 — Verify (minimal + targeted)
Verify against ACCEPTANCE scoped to the task(s).
Use Playwright only if explicitly required by contract (see `references/03-browser-verification-policy.md`).
Report what you verified and what you did not verify (and why).
If verification fails: fix only within current task scope; otherwise STOP and follow deviation/doc update protocol.

## Step 6 — Commit per task
Stage only relevant changes and commit per task (do not mix TaskIDs).

## Step 7 — Update TASKS + CHECKPOINT
- Update `TASKS.md` → `## Execution status` (status/current/last updated)
- Update `CHECKPOINT.md` (10–25 lines, resumable)
- Commit docs update if docs changed
- Docs commit message: `docs(<slug>): update execution status after <TaskID(s)>`

## Step 8 — Push
Push `impl/<slug>` after each chunk.
If push fails: STOP and report exact error output.

## Step 9 — Report
Report branch, tasks implemented, commits, files changed, verification, updated execution status, checkpoint summary, and deviations (if any).
