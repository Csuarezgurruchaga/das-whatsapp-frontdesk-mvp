---
name: implement-from-spec
description: Implement code strictly from an approved SPEC/PLAN/TASKS/ACCEPTANCE. Execute atomic tasks in small chunks, keep the spec as source of truth, update TASKS execution status, and maintain a lightweight CHECKPOINT.md for safe resumption across sessions.
metadata:
  short-description: Execute implementation from SPEC/PLAN/TASKS/ACCEPTANCE (atomic chunks + spec-anchored + CHECKPOINT)
---

# Purpose

Implement code **only** after the design has been finalized via `spec-interview`.

This skill is **execution-only** and **task-driven**:
- The SPEC is the contract.
- PLAN is the strategy.
- TASKS is the executable backlog (atomic work units).
- ACCEPTANCE is the verification target.

This skill also maintains a **lightweight CHECKPOINT** to safely resume work across sessions without reloading full history.

---

# Inputs (required)

- `<slug>` identifying the spec (required)
- Repository state (existing codebase)

You may also receive a requested scope:
- “Do the next task”
- “Do tasks T1.1 and T1.2”
- “Do Phase 0”

If not provided, default to the **Current task** from `TASKS.md` → `Execution status`.

---

# Required files (must exist)

The spec directory MUST exist:
- `docs/specs/<slug>/`

And MUST contain:
- `SPEC.md`
- `PLAN.md`
- `TASKS.md`
- `ACCEPTANCE.md`

Additionally, this skill MUST create/maintain:
- `CHECKPOINT.md`

If ANY required file among SPEC/PLAN/TASKS/ACCEPTANCE is missing:
- Stop immediately.
- Explain what is missing.
- Recommend returning to `spec-interview`.
- Do NOT implement anything.

---

# Preconditions (MUST enforce)

Before writing any code, you MUST verify:

1) `SPEC.md` contains an "Open Questions" section AND it is empty  
   - If not empty: STOP and send the user back to `spec-interview`.

2) `SPEC.md` contains the spec-anchored statement (verbatim):

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

3) `TASKS.md` contains `## Execution status` as the LAST section  
   - If missing/malformed: STOP and recommend fixing via `spec-interview`.

4) `TASKS.md` has minimally:
   - Status
   - Current task
   - Last updated

If `Status: DONE`:
- STOP (nothing to implement).

---

# Environment & dependency management (mandatory)

This skill MUST keep dependency installation isolated and reproducible.

If the selected task involves Python, you MUST use `.venv/`.
If the selected task involves JavaScript/TypeScript (frontend), you MUST use the repo’s Node package manager workflow.

You MUST NOT install dependencies globally (neither Python nor Node).

---

## Python virtual environment rule (mandatory)

If the repo contains Python code OR the selected task involves running Python:

### Always use `.venv/`
- You MUST use a project-local virtual environment at `.venv/`.
- If `.venv/` does NOT exist, you MUST create it.
- If `.venv/` exists, you MUST reuse it across sessions (do NOT create another env elsewhere).

### pip baseline (mandatory)
After creating/activating `.venv/`, you MUST upgrade pip inside the venv BEFORE any installs:
- `python -m pip install --upgrade pip`

### Dependency file policy (supports bootstrapping new projects)

#### If a dependency definition file exists
Install dependencies inside `.venv/` using one of:
- `requirements.txt`
- `requirements-dev.txt`

#### If NO dependency definition file exists (new project bootstrap)
If the project is being created from scratch and dependencies are not yet defined:
- You MUST create a minimal `requirements.txt` (it may be empty initially)
- You MUST continue execution using `.venv/`

If the chosen task explicitly requires specific Python dependencies to proceed:
- You MUST add ONLY the minimum required packages to `requirements.txt`
- Do NOT guess versions unless SPEC/TASKS defines them

A task that introduces new Python dependencies is NOT complete unless:
- the dependency is recorded in `requirements.txt`
- verification runs using `.venv/`

---

## Frontend (JavaScript/TypeScript) dependency rule (mandatory)

If the repo contains frontend JS/TS code OR the selected task involves frontend tooling:

### Always use a package-lock based workflow
You MUST install dependencies using the repo-defined package manager:

- If `package-lock.json` exists → use `npm`
- If `yarn.lock` exists → use `yarn`
- If `pnpm-lock.yaml` exists → use `pnpm`

Rules:
- You MUST NOT mix package managers in the same repo.
- You MUST NOT delete lockfiles unless the task explicitly requires it.
- You MUST commit lockfile changes if dependencies change.

### Bootstrap for new frontend projects
If `package.json` does not exist and the project is being created from scratch:
- You MUST create a minimal `package.json`
- You MUST continue execution with the chosen package manager

If the chosen task explicitly requires specific frontend dependencies:
- You MUST add ONLY the minimum required packages
- Prefer using the lockfile to keep installs reproducible

A task that introduces new frontend dependencies is NOT complete unless:
- dependencies are recorded in `package.json`
- the lockfile is updated consistently
- verification/build runs using the repo’s Node workflow

---

## Session resumption rule (Codex continuity)

This skill is designed to be resumable across sessions.

Therefore:
- If a new Codex session starts and `.venv/` already exists, you MUST reuse it.
- If a lockfile already exists (`package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml`), you MUST keep using it.

---

# Browser verification policy (web apps)

This skill MAY use Playwright for browser-level verification, but ONLY when required by contract.

Playwright MUST be used only if:
- the current task changes user-facing behavior (UI, routing, auth, forms), AND
- ACCEPTANCE.md or TASKS.md explicitly requires browser-level verification.

If those conditions are not met:
- Do NOT run browser automation.
- Do NOT add E2E tests.
- Limit verification to repo-defined checks (unit tests / lint / build).

Chrome DevTools MCP MUST NOT be used for functional E2E validation unless the task explicitly requires
performance/network/rendering diagnostics.


# Hard execution guardrails (context + safety)

- You MUST implement **at most 1–2 tasks per run** (one “chunk”).
- You MUST NOT implement multiple phases in a single run.
- You MUST keep diffs small and reviewable.
- You MUST NOT add “bonus features” or refactor unrelated code.
- If a task implies large changes: STOP and recommend splitting tasks (return to `spec-interview` to adjust TASKS).

---

# Strict execution rules

- Do NOT redesign.
- Do NOT propose alternatives.
- Do NOT re-open decisions already documented.
- Do NOT add features not explicitly listed in SPEC/TASKS.
- Do NOT “improve” the design.
- Do NOT refactor unrelated code.

If something is unclear:
- Check SPEC first.
- Then check the task definition in TASKS.
- Then check PLAN.
- If still unclear: STOP and report the ambiguity.
- Do NOT guess.

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
- What must NOT be built
- Key constraints
- Current execution status (from TASKS)
- Which task(s) you will implement in this run

Task selection priority:
1) User-requested tasks (if explicit and valid)
2) Otherwise `Current task` from Execution status

---

## Step 2 — Validate task scope (mandatory)

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
- Recommend returning to `spec-interview` to fix TASKS.md
- Do NOT implement

---

## Step 3 — Implement (task-driven)

Implement ONLY what is required to satisfy:
- the chosen TASK(s)
- the SPEC constraints

Rules:
- Touch only files implied by the task(s).
- Preserve existing conventions and style.
- Prefer minimal, reviewable diffs.
- If you need a new file/module, it must be justified by task outputs.

### If you discover a necessary deviation (spec-anchored rule)

If implementation forces a change to requirements (API shape, flow behavior, constraints, edge-case semantics):
- STOP immediately (no partial hacks)
- Propose a SPEC update with:
  - exact change
  - why it’s necessary
  - impact on TASKS + ACCEPTANCE
- Update ONLY docs first (SPEC/TASKS/ACCEPTANCE + SPEC Changelog)
- Continue implementation ONLY after docs are consistent

You MUST record the change in SPEC Changelog as:
- YYYY-MM-DD — <change summary>
  - reason: <why it changed>
  - impact: <what updated: tasks/plan/acceptance>

---

## Step 4 — Verification (minimal + targeted)

### Browser smoke verification (conditional)

If the task impacts user-facing behavior (UI, routing, auth, forms) AND ACCEPTANCE/TASKS require browser-level validation:
- You MUST run a minimal Playwright smoke check (happy path only).
- Keep it small and reliable (avoid flaky waits, no broad E2E suites unless TASKS explicitly require them).
- Report the exact checks performed and outcome.

Otherwise:
- Do NOT run Playwright.

Verify against ACCEPTANCE.md, but keep it scoped:
- Run tests if they exist.
- If no tests exist, perform verification steps from each implemented task.

You MUST report:
- What you verified
- What you did NOT verify (and why)

You MUST NOT add new tooling unless PLAN/TASKS explicitly say so.

---

## Step 5 — Update TASKS Execution status (mandatory)

After successful implementation of the task(s), update `TASKS.md` → `## Execution status`:

Rules:
- Status transitions:
  - NOT_STARTED → IN_PROGRESS (when first task begins)
  - IN_PROGRESS stays until all tasks complete
  - DONE only when all tasks are complete
- Move Current task to the next pending task
- Update Last updated = YYYY-MM-DD

If all tasks are complete:
- Set Status: DONE
- Current task: (none)

---

## Step 6 — Maintain CHECKPOINT.md (mandatory)

This skill MUST create/update:
- `docs/specs/<slug>/CHECKPOINT.md`

### Objective of CHECKPOINT.md
Provide a short “resume safely” snapshot:
- what was completed in practice
- what is next
- important constraints/gotchas discovered during implementation
- safe resume instructions

### Hard rules for CHECKPOINT.md
- MUST be concise (aim: 10–25 lines)
- MUST NOT duplicate TASKS definitions
- MUST NOT introduce new requirements (those belong in SPEC.md)
- MUST be updated after every run that changes code

### Required CHECKPOINT.md structure (enforce)

`CHECKPOINT.md` MUST contain:

1) Title + slug  
2) Last updated date  
3) Completed (task IDs)  
4) Current / Next (task IDs)  
5) Important constraints (max 3 bullets)  
6) Gotchas / Risks discovered (max 5 bullets)  
7) Safe resume instructions (max 5 bullets)  

Example structure (use exactly these headings):

    # CHECKPOINT — <slug>

    Last updated: YYYY-MM-DD

    ## Completed
    - T0.1 ...
    - T1.1 ...

    ## Current / Next
    - Next task: T1.2 ...
    - Status: READY

    ## Important constraints
    - ...

    ## Gotchas / Risks discovered
    - ...

    ## Safe resume instructions
    - ...

---

## Step 7 — Report (concise + factual)

After implementation, report:

1) Tasks implemented in this run:
   - T?.? title — done condition satisfied (yes/no)

2) Files changed:
   - path — reason

3) Verification:
   - Acceptance criteria impacted: Passed / Failed / Not checked
   - Test results (if applicable)

4) Execution status updates:
   - New status + next task

5) CHECKPOINT update summary:
   - What changed in CHECKPOINT.md (1–3 bullets)

6) Deviations (if any):
   - Must link back to SPEC Changelog entry

---

# Failure mode

If at any point SPEC/TASKS/ACCEPTANCE are insufficient to implement safely:
- Stop.
- Explain precisely what is missing.
- Recommend returning to `spec-interview`.

This skill values **discipline over creativity**.