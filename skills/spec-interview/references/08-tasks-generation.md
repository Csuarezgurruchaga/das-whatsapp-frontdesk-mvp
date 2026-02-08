## Step 4 — Generate TASKS.md (atomic tasks, mandatory)

After PLAN.md, you MUST create `TASKS.md` that converts the PLAN into:
**atomic, reviewable tasks**  
that can be implemented in **small chunks** safely

### Definition: “atomic task”
A task is atomic if it is:
- small enough to implement without exceeding context
- independently testable or verifiable
- has clear inputs/outputs
- has minimal dependencies
- has a tight “done condition”

### Hard rules for TASKS.md

- Tasks MUST be ordered.
- Tasks MUST be grouped by phase.
- Each task MUST have:
  - **Goal**
  - **Inputs**
  - **Outputs**
  - **Steps (tiny)**
  - **Done condition**
  - **Depends on** (MUST be a bracketed list of task IDs like `[T0.1, T1.2]` or `[]`)
  - **Risks**
  - **Test/Verification**
- Prefer **5–15 tasks total**.
- If tasks would exceed ~15, you MUST suggest splitting the spec (use guardrails).

### TASKS.md format (mandatory)

Use this exact structure:

# TASKS

## Phase 0 — Setup / scaffolding
- T0.1 <task title>
  - Goal:
  - Inputs:
  - Outputs:
  - Steps:
  - Done condition:
  - Depends on: []
  - Risks:
  - Test/Verification:

## Phase 1 — Core logic
(Generated tasks will appear here. Replace this placeholder with T1.x tasks.)

## Phase 2 — Integration
(Generated tasks will appear here. Replace this placeholder with T2.x tasks.)

## Phase 3 — Observability / hardening
(Generated tasks will appear here. Replace this placeholder with T3.x tasks.)

## Phase 4 — Release / rollout
(Generated tasks will appear here. Replace this placeholder with T4.x tasks.)

### Dependency rules (mandatory)

In `TASKS.md`, each task MUST include:

- `Depends on: []` for tasks with no prerequisites, OR
- `Depends on: [T0.1, T1.2]` referencing existing task IDs only

Hard rules:
- Dependencies MUST reference existing task IDs only (no free-text).
- Cycles are not allowed. If a cycle would occur, restructure tasks.
- Prefer minimal dependencies: only list true blockers.

### Chunking rule (mandatory)

In `TASKS.md`, after listing all phases and tasks, you MUST include a `Chunking guidance` section containing:

- **Suggested implementation chunk size:** 1–2 tasks per chunk
- **Review cadence:** after each chunk, verify acceptance criteria impacted by those tasks
- **Stop points:** “safe to stop here” markers after phases

### Execution status block (mandatory)

At the very end of `TASKS.md`, you MUST include an `Execution status` section to make the work resumable across sessions.

This section MUST be the last section in the file.

**Initial value requirement (mandatory)**
When generating `TASKS.md` for the first time, you MUST initialize it exactly as follows:

    ## Execution status
    - Status: NOT_STARTED
    - Current task: T0.1
    - Completed tasks: (optional)
    - Last updated: YYYY-MM-DD
