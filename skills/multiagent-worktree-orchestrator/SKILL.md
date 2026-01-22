---
name: multiagent-worktree-orchestrator
description: Orchestrate parallel implementation of multiple finalized specs using git worktrees and multi-agents. Use after `$spec-interview` has produced `docs/specs/<slug>/{SPEC.md,PLAN.md,TASKS.md,ACCEPTANCE.md}` with no Open Questions. Create a worktree + `impl/<slug>` branch per spec, spawn one implementer agent per worktree (write access limited to that worktree), spawn read-only review/test agents, then merge into an integration branch (default `dev`) and suggest verification commands.
---

# Purpose

Run multiple specs in parallel safely by isolating each implementation in its own **git worktree** and keeping a single thread responsible for integration.

# Hard rules (community best practices)

- Enforce **single-writer per worktree**: never allow two agents to edit the same worktree.
- Treat the **main thread as the integrator**: only the main thread merges/pushes the integration branch.
- Keep subagents **role-scoped**:
  - Implementers may write code, but only inside their assigned worktree.
  - Reviewers/testers are **read-only** (no edits, no git writes).
- Do not proceed if the spec is not finalized.

# Preconditions (must verify before spawning implementers)

For each `<slug>`:

- `docs/specs/<slug>/SPEC.md` exists and has an **Open Questions** section that is empty.
- `docs/specs/<slug>/PLAN.md`, `TASKS.md`, and `ACCEPTANCE.md` exist.
- `TASKS.md` contains `## Execution status` and it is well-formed.

Repo-level:

- You are in a git repo (`git rev-parse --show-toplevel` works).
- Working tree is clean in the main repo (no uncommitted changes).

If any precondition fails:

- Stop.
- Tell the user exactly what is missing.
- Recommend running `$spec-interview <slug>` (or finishing Open Questions) before continuing.

# Inputs

- `Slugs`: 2–4 slugs is the sweet spot (avoid spawning >4 implementers at once).
- `Integration branch`:
  - Default: `dev`.
  - If `dev` does not exist: ask whether to create it from `main` (or use `main` as integration).
- `Worktree root`:
  - Default: `../.worktrees/<repo-name>/` (sibling folder of the repo).
  - If the user prefers inside the repo: use `<repo-root>/.worktrees/` and ensure it is ignored.

# Language policy

- Ask questions and report in Spanish.
- Keep code/paths/commands/identifiers exactly as written.

# Workflow

## Step 1 — Confirm parallelization is safe

For the requested slugs, confirm the work is reasonably independent.

- If two specs touch the same core module/API heavily: recommend sequential execution instead of parallel.

## Step 2 — Prepare worktrees (main thread only)

For each `<slug>`:

- Compute:
  - `branch = impl/<slug>`
  - `path = <worktree_root>/<slug>`

- Create the worktree safely:
  - If `path` already exists: ask whether to reuse, delete, or choose a new path.
  - If `branch` already exists: attach a worktree to it.
  - Otherwise: create `branch` from the integration branch and add the worktree.

Preferred command shapes (choose the safest variant for the current state):

- Existing branch:
  - `git worktree add <path> <branch>`
- New branch from integration:
  - `git worktree add -b <branch> <path> <integration-branch>`

Do not rewrite existing branches with `-B` unless the user explicitly approves.

## Step 3 — Spawn implementer agents (one per worktree)

Spawn one implementer per `<slug>`.

Implementer constraints (must include verbatim in each subagent prompt):

- "You are the ONLY writer for this worktree. Do not edit any other worktree." 
- "Work only inside: `<path>` (start by `cd <path>`)." 
- "Follow `$implement-from-spec-git <slug>` exactly."
- "Do at most 1–2 TASKS per run (one chunk)."
- "Commit rules and push rules from the skill are mandatory."
- "If you hit ambiguity or a required spec change: STOP and request a SPEC/TASKS/ACCEPTANCE update (do not hack around it)."

Implementer deliverable (must be included in prompt):

- Branch name
- Tasks implemented (IDs)
- Commits created (hash + message)
- Verification performed (or explicitly not performed)
- Next task according to `TASKS.md`

## Step 4 — Spawn review agents (read-only)

After implementers finish a chunk, spawn a reviewer per `<slug>`.

Reviewer rules:

- Read-only: no edits, no git writes, no commands that modify state.
- Review for:
  - Spec adherence (SPEC/PLAN/TASKS)
  - Risky diffs / missing edge cases
  - Whether ACCEPTANCE criteria are fully covered

Reviewer output (short):

- Issues (must-fix)
- Nits (optional)
- Acceptance coverage gaps
- Recommendation: approve / request changes

## Step 5 — Suggest verification commands (do not run)

For each `<slug>` and for integration, suggest a minimal verification set.

- Prefer existing repo commands (e.g. `make test`, `pytest -q`, `npm test`, `pnpm test`, etc.).
- If nothing obvious exists, suggest a focused manual check aligned with ACCEPTANCE.

Do not execute tests unless the user explicitly requests it.

## Step 6 — Integrate (main thread only)

Once the user accepts the reviews and/or required fixes are applied:

- Merge each `impl/<slug>` into the integration branch one at a time.
- Ask before:
  - merging into `dev`
  - pushing `dev` to origin

If merge conflicts occur:

- Resolve in the main thread.
- If the resolution requires deeper feature knowledge, ask the relevant implementer for guidance.

After merges, propose the integration verification commands.

# Orchestrator reporting format (Spanish)

At the end, report:

- Specs/branches:
  - `<slug>` → `impl/<slug>` → worktree path
- Status per spec:
  - Current task / next task
  - Review result (approved / changes requested)
- Integration status:
  - Merged into `<integration-branch>` (yes/no)
  - Suggested verification commands (not executed)

