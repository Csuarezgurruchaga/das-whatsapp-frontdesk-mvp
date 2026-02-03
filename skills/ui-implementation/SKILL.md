---
name: ui-implementation
description: "Implement browser UI strictly from docs/specs/<slug> (SPEC/PLAN/TASKS/ACCEPTANCE). Frontend-only: components, routing, responsive layout, accessibility, UX states. Uses Git discipline (impl/<slug>, 1 commit per task, push per chunk). Playwright only if required. NOT for backend."
metadata:
  short-description: "Implement UI from spec (frontend-only + Git discipline + optional Playwright)."
---

# Purpose

Implement **frontend / web UI** code **only** after the design has been finalized via `frontend-spec-interview` (or an equivalent spec package).

This skill is **execution-only**, **task-driven**, and **Git-disciplined**:
- SPEC is the contract (source of truth)
- PLAN is the strategy
- TASKS is the executable backlog (atomic units)
- ACCEPTANCE is the verification target
- Git history mirrors TASK execution (auditable + resumable)

This skill is also **spec-anchored**:
- If implementation deviates, you MUST update SPEC + TASKS + ACCEPTANCE and record it in SPEC Changelog **before** continuing.

---

# Inputs (required)

- `<slug>` identifying the spec (required)
- Repo state

Optional user scope:
- “Do the next task”
- “Do tasks T1.1 and T1.2”
- “Do Phase 0”
- “Only do UI foundations”

If no scope is provided:
- Default to the `Current task` from `TASKS.md` → `Execution status`.

---

# Required files (must exist)

The spec directory MUST exist:
- `docs/specs/<slug>/`

And MUST contain:
- `SPEC.md`
- `PLAN.md`
- `TASKS.md`
- `ACCEPTANCE.md`

This skill MUST create/maintain:
- `CHECKPOINT.md`

If ANY required file among SPEC/PLAN/TASKS/ACCEPTANCE is missing:
- STOP immediately.
- Explain what is missing.
- Recommend returning to `frontend-spec-interview`.
- Do NOT implement anything.

---

# Preconditions (MUST enforce)

Before writing code, you MUST verify:

1) `SPEC.md` contains an "Open Questions" section AND it is empty  
   - If not empty: STOP → return to `frontend-spec-interview`.

2) `SPEC.md` contains the spec-anchored statement (verbatim):

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

3) `TASKS.md` contains `## Execution status` as the LAST section  
   - If missing/malformed: STOP → return to `frontend-spec-interview`.

4) `TASKS.md` includes:
   - Status
   - Current task
   - Last updated

If `Status: DONE`:
- STOP (nothing to implement).

---

# Environment & dependency management (mandatory)

This skill MUST keep dependency installation isolated and reproducible.

## Frontend (JavaScript/TypeScript) dependency rule (mandatory)

If the repo contains frontend JS/TS code OR the selected task involves frontend tooling:

### Always use a lockfile-based workflow
You MUST install dependencies using the repo-defined package manager:

- If `package-lock.json` exists → use `npm`
- If `yarn.lock` exists → use `yarn`
- If `pnpm-lock.yaml` exists → use `pnpm`

Rules:
- You MUST NOT mix package managers in the same repo.
- You MUST NOT delete lockfiles unless the task explicitly requires it.
- You MUST commit lockfile changes if dependencies change.
- Prefer CI-friendly installs:
  - `npm ci` when `package-lock.json` exists
  - `pnpm i --frozen-lockfile` when using pnpm
  - `yarn install --frozen-lockfile` when using yarn

### Bootstrap for new frontend projects (only if SPEC explicitly requires creating the app)
If `package.json` does not exist and the project is being created from scratch:
- You MUST create a minimal `package.json`
- You MUST continue execution with the chosen package manager
- Do NOT add dependencies unless SPEC/TASKS requires it

A task that introduces new frontend dependencies is NOT complete unless:
- dependencies are recorded in `package.json`
- the lockfile is updated consistently
- verification/build runs using the repo’s Node workflow

---

# Session resumption rule (Codex continuity)

This skill is designed to be resumable across sessions.

Therefore:
- If a lockfile already exists, you MUST keep using it.
- If `impl/<slug>` branch exists, you MUST continue work there.

---

# Browser verification policy (web apps)

This skill MAY use Playwright for browser-level verification, but ONLY when required by contract.

Playwright MUST be used only if:
- the current task changes user-facing behavior (UI, routing, auth, forms), AND
- ACCEPTANCE.md or TASKS.md explicitly requires browser-level verification.

If those conditions are not met:
- Do NOT run Playwright.
- Do NOT add E2E tests.
- Limit verification to repo-defined checks (typecheck/lint/unit/build).

Chrome DevTools MCP MUST NOT be used for functional E2E validation unless the task explicitly requires performance/network/rendering diagnostics.

---

# Hard execution guardrails

- You MUST implement **at most 1–2 tasks per run** (one chunk).
- You MUST NOT implement multiple phases in a single run.
- You MUST keep diffs small and reviewable.
- You MUST NOT add “bonus features” or refactor unrelated code.
- If a task implies large changes: STOP and recommend splitting tasks (return to spec interview to adjust TASKS).

---

# Strict execution rules

- Do NOT redesign.
- Do NOT propose alternatives.
- Do NOT re-open decisions already documented.
- Do NOT add features not explicitly listed in SPEC/TASKS.
- Do NOT “improve” the design beyond what the spec requires.
- Do NOT refactor unrelated code.

If something is unclear:
- Check SPEC → then TASK definition → then PLAN.
- If still unclear: STOP and report ambiguity.
- Do NOT guess.

---

# Frontend quality gates (MANDATORY for every chunk)

Every chunk MUST maintain:

## A) Responsive (mobile-first)
- Default layout works on small screens
- Breakpoints enhance tablet/desktop
- No horizontal overflow

## B) Accessibility baseline
- semantic HTML (button/nav/main/header)
- keyboard navigation works
- focus states visible
- labels/aria for inputs
- respect `prefers-reduced-motion`

## C) UX States (when applicable)
If the task touches data/async states:
- loading state
- empty state
- error state

## D) Maintainability
- consistent tokens (CSS variables or consistent Tailwind usage)
- avoid scattered hardcoded colors
- reusable components and clear props

---

# Git discipline (mandatory)

## Branch rules (hard)

All implementation MUST happen on a branch:

- Branch name MUST be:
  - `impl/<slug>`

Examples:
- `impl/pricing-page-revamp`
- `impl/admin-dashboard-v2`

If currently on `main` (or any protected branch):
- STOP and create/switch to `impl/<slug>` before writing code.

## Commit rules (hard)

- **1 task = 1 commit** (preferred)
- If a task truly needs 2 commits, it MUST still remain task-scoped (no cross-task mixing)
- Every commit message MUST include:
  - `<type>(<slug>): <TaskID> <short title>`

Allowed commit types:
- `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `style`

Commit message examples:
- `feat(pricing-page-revamp): T2.1 build hero + nav layout`
- `fix(admin-dashboard-v2): T3.2 prevent overflow on mobile tables`
- `docs(pricing-page-revamp): update execution status after T2.1`

## Push rules (hard)

- You MUST push after each chunk (after 1–2 tasks) so the work is persisted remotely.
- If the push fails, STOP and report the error.

---

# Execution workflow

## Step 1 — Load and summarize the contract (brief)

Read:
- `SPEC.md`
- `PLAN.md`
- `TASKS.md`
- `ACCEPTANCE.md`

Then produce a concise summary (5–8 bullets):
- What must be built
- What must NOT be built (non-goals)
- UI constraints (responsive/a11y/motion)
- Current execution status (from TASKS)
- Which task(s) you will implement in this run

Task selection priority:
1) User-requested tasks (if explicit and valid)
2) Otherwise `Current task` from Execution status

---

## Step 2 — Ensure correct branch (mandatory)

All implementation MUST happen on:
- `impl/<slug>`

### Bootstrap rule (new repositories)
If `main` and `dev` do not exist yet (new project):
- You MUST initialize the repo if needed.
- You MUST create `main` first.
- You MUST create `dev` from `main`.

After that:
- Continue with the normal branch rules below.

### Branch base rule (normal flow)
- If `dev` exists, you MUST create/sync `impl/<slug>` from `dev`.
- Otherwise, create/sync `impl/<slug>` from `main`.

### Rules
- You MUST NOT implement directly on `main`.
- You SHOULD NOT implement directly on `dev` (dev is the integration branch).

### Actions
If `impl/<slug>` does not exist:
- Create it from the correct base branch, then switch to it.

If `impl/<slug>` already exists:
- Switch to it and continue work there.

---

## Step 3 — Validate task scope (mandatory)

For each chosen task (max 2), verify it is well-defined:
- Goal
- Inputs
- Outputs
- Steps
- Done condition
- Dependencies
- Risks
- Test/Verification

If any field is missing or ambiguous:
- STOP
- Explain what is missing
- Recommend returning to `frontend-spec-interview` to fix TASKS.md
- Do NOT implement

---

## Step 4 — Implement task(s) (task-driven)

### Browser smoke verification (conditional)
If the task impacts user-facing behavior (UI, routing, forms, auth) AND ACCEPTANCE/TASKS require browser-level validation:
- You MUST run a minimal Playwright smoke check (happy path only).
- Keep it small and reliable (avoid flaky waits, avoid broad suites).
- Report the exact checks performed and outcome.

Otherwise:
- Do NOT run Playwright.
- Do NOT add new E2E tests.

Implement ONLY what is required to satisfy:
- the chosen task(s)
- the SPEC constraints

Rules:
- Touch only files implied by the task(s).
- Preserve existing conventions.
- Keep diffs minimal and reviewable.

---

## Step 4A — Playwright smoke check format (if required)

If Playwright must be run, it MUST remain minimal:

### Viewports (recommended)
- Mobile: 390×844
- Tablet: 768×1024
- Desktop: 1440×900

### Smoke assertions (minimal)
Verify at minimum:
- app renders (not blank)
- primary headline/CTA visible on mobile
- no obvious overlap/clipping
- no horizontal overflow

### Artifact naming (recommended)
If screenshots are produced:
- `artifacts/ui-mobile.png`
- `artifacts/ui-tablet.png`
- `artifacts/ui-desktop.png`

### Limits
- Max 1 Playwright run + 1 fix pass
- Do NOT chase pixel perfection

---

## Step 4B — Spec-anchored deviation rule (STRICT)

If implementation forces a change to requirements (flow behavior, constraints, edge-case semantics):
- STOP immediately (no hacks)
- Propose a SPEC update with:
  - exact change
  - why it’s necessary
  - impact on TASKS + ACCEPTANCE
- Update docs first (SPEC/TASKS/ACCEPTANCE + SPEC Changelog)
- Continue implementation ONLY after docs are consistent

Changelog entry format:
- YYYY-MM-DD — <change summary>
  - reason: <why it changed>
  - impact: <what updated: tasks/plan/acceptance>

---

## Step 5 — Verify (minimal + targeted)

Verify against ACCEPTANCE.md, scoped to the tasks implemented:
- Run repo checks if they exist (typecheck/lint/test/build)
- Otherwise use each task’s Test/Verification steps

Report:
- What you verified
- What you did NOT verify (and why)

Do NOT add tooling unless PLAN/TASKS explicitly require it.

---

## Step 6 — Commit per task (mandatory)

After completing each task:
- Stage only relevant changes
- Commit using the required format:
  - `<type>(<slug>): <TaskID> <short title>`

Rules:
- Do NOT mix two tasks into one commit
- Do NOT commit unrelated refactors

---

## Step 7 — Update TASKS Execution status + CHECKPOINT (mandatory)

After the chunk is complete (after 1–2 tasks):

### 7A) Update `TASKS.md` → `## Execution status`
- Status transitions:
  - NOT_STARTED → IN_PROGRESS (first chunk)
  - DONE only when all tasks finished
- Set Current task to next pending task
- Update Last updated = YYYY-MM-DD

### 7B) Update `CHECKPOINT.md`
Location:
- `docs/specs/<slug>/CHECKPOINT.md`

Hard rules:
- Keep it concise (10–25 lines)
- Do NOT duplicate TASK definitions
- Do NOT introduce new requirements (those belong in SPEC)

Required structure:

# CHECKPOINT — <slug>

Last updated: YYYY-MM-DD

## Completed
- T?.? ...
- T?.? ...

## Current / Next
- Next task: T?.? ...
- Status: READY

## Important constraints
- ...

## Gotchas / Risks discovered
- ...

## Safe resume instructions
- ...

### 7C) Commit docs update (mandatory if docs changed)
Commit message MUST be:

- `docs(<slug>): update execution status after <TaskID(s)>`

Example:
- `docs(pricing-page-revamp): update execution status after T2.1`

---

## Step 8 — Push (mandatory)

Push the branch to remote after each chunk:

- `git push -u origin impl/<slug>` (first push)
- `git push` (subsequent pushes)

If push fails:
- STOP and report error details.

---

## Step 9 — Report (concise + factual)

After the chunk, report:

1) Branch:
- `impl/<slug>`

2) Tasks implemented:
- T?.? title — done condition satisfied (yes/no)

3) Commits created:
- `<hash>` — message

4) Files changed:
- path — reason

5) Verification:
- Acceptance criteria impacted: Passed / Failed / Not checked
- Test results (if applicable)
- Playwright smoke (only if required): Ran / Skipped + why

6) Execution status:
- New Status
- Next task

7) CHECKPOINT summary:
- What changed (1–3 bullets)

8) Deviations (if any):
- Must link back to SPEC Changelog entry

---

# Optional: PR guidance (only if user asks)

If the user requests a PR:
- Create PR from `impl/<slug>` → `main`
- Title format:
  - `(<slug>) Phase <n>: <short summary>`
- Include checklist:
  - Implemented tasks: ...
  - Verification: ...
  - Acceptance status: ...

---

# Failure mode

If at any point SPEC/TASKS/ACCEPTANCE are insufficient to implement safely:
- STOP
- Explain precisely what is missing
- Recommend returning to `frontend-spec-interview`

This skill values **discipline over creativity**.
