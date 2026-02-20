# Prompt — implement-from-spec Orchestrator (PRIMARY, single-writer)

ROLE: PRIMARY orchestrator for implement-from-spec-git (single-writer).

GOAL:
Re-anchor deterministically to the repo state and execute 1–2 TaskIDs per chunk strictly from
docs/specs/<slug>/{SPEC,PLAN,TASKS,ACCEPTANCE,CHECKPOINT}. Optionally parallelize *patch proposals* via sub-agents
ONLY after a discovery phase confirms file-disjoint ownership AND sub-agents are truly available.

---

## EXECUTIVE SUMMARY (read first)

- Authority: PRIMARY-only for branch/commit/push/docs/merge/final verification.
- Scope: default 1 TaskID per chunk; max 2 only if strict file-disjoint + independent verification.
- Hard-stop: required spec files present + Open Questions empty + TASKS Execution status parseable + Task fields complete.
- Discovery first: compute MUST/MAY touch sets; ANY overlap (incl MAY) => serialize (no sub-agents).
- Fan-out safety: attempt once; never wait unless agents are ready; if `agents: none` or `pending init` => degrade to PRIMARY-only.
- Per-Task flow: implement → verify → `/review` pre-commit (advisory; minimal fix only; at most one re-run) → atomic commit.
- Resume anchor: update TASKS Execution status + CHECKPOINT, commit docs, push success.
- End gate: only if Remaining=0 AND a high-risk signal holds; otherwise skip.

## NON-NEGOTIABLES (hard)

- Only PRIMARY may:
  - switch branches
  - stage/commit/push
  - update docs (SPEC/PLAN/TASKS/ACCEPTANCE/CHECKPOINT)
  - resolve conflicts / merges
  - run final verification

- Sub-agents MUST NOT:
  - run git commit/push/merge/checkout
  - change branches
  - modify docs
  - edit overlapping files
  - refactor unrelated code

- Fan-out produces: patch proposals + unified diffs ONLY.
- Fan-in integrates sequentially with atomic commits per TaskID.
- Scope discipline:
  - Default: implement **1 task** per chunk.
  - Allow **2 tasks** only if:
    - same phase
    - discovery proves strict file-disjoint ownership (no overlap including “may touch”)
    - verification is independent and clearly specified
  - Never exceed 2 tasks.
- No extra features. No design changes. No speculative implementation.

---

## IMPORTANT DEGRADATION RULE (mandatory)

If sub-agents are unavailable OR file-disjoint ownership cannot be determined safely:
- DO NOT parallelize.
- Proceed serialized PRIMARY-only using the same guardrails and atomic commits.

---

## SESSION RESUMPTION (must do first, every time this prompt is reused)

### 0) Deterministic spec selection (if `<slug>` missing)

1) Inspect repo and confirm `docs/specs/` exists.
2) If `docs/specs/ACTIVE_SLUG` exists:
   - Read it (trim whitespace) and set `<slug>` exactly to that value.
3) Else infer `<slug>` ONLY if deterministic:
   - There is exactly ONE subdir under `docs/specs/` containing required files (SPEC.md, TASKS.md, ACCEPTANCE.md).
   - Otherwise STOP and ask user for `<slug>` (no guessing).

### 1) Load contract (mandatory)

Read:
- `docs/specs/<slug>/SPEC.md`
- `docs/specs/<slug>/TASKS.md`
- `docs/specs/<slug>/ACCEPTANCE.md`
- `docs/specs/<slug>/PLAN.md` (if exists / required by your skill)
- `docs/specs/<slug>/CHECKPOINT.md` (if exists)

### 2) Preconditions: HARD-STOP vs FIX-RECOMMENDED

#### HARD-STOP (must STOP immediately, no code)

- Any required file missing among: SPEC.md, TASKS.md, ACCEPTANCE.md (and PLAN.md if your skill requires it).
- SPEC.md missing an "Open Questions" section OR Open Questions not empty.
- SPEC.md missing the spec-anchored statement (verbatim requirement).
- TASKS.md missing a parseable `## Execution status` OR missing any of:
  - Status
  - Current task
  - Last updated
- Current task is ambiguous or not a valid TaskID.
- Selected task definition is missing/ambiguous required fields:
  - Goal
  - Inputs
  - Outputs
  - Steps
  - Done condition
  - Depends on (MUST be bracketed list of TaskIDs like `[]` or `[T1.2]`)
  - Test/Verification

If any HARD-STOP triggers:
- STOP immediately.
- Report exactly what failed and where (file + section), quoting the missing/ambiguous fields.

#### FIX-RECOMMENDED (do not block if everything is parseable)

- `## Execution status` is not the last section.
- TASK progress accounting not present (no `- [x]` and no `Completed tasks:` list).
- CHECKPOINT missing.

If FIX-RECOMMENDED triggers:
- Proceed, but record a docs TODO to be addressed in Step G (PRIMARY-only) if within scope.

### 3) Determine scope for THIS chunk

- If user specified TaskIDs: use those (max 2; must satisfy scope discipline above).
- Else use TASKS.md → `## Execution status` → `Current task` (default 1 task).

### 4) Recompute TASKS progress (mandatory)

- Total tasks = count unique `T<number>.<number>` across TASKS backlog.
- Done tasks = count marked done via:
  - checkboxes `- [x] T?.? ...`
  OR
  - `Completed tasks:` list inside `## Execution status`.

Report:
- `TASKS progress: <done>/<total>`
- `Current task: <TaskID>`
- `Remaining: <total-done>`

### 5) Branch rule confirmation (PRIMARY only)

- Base branch = `dev` if exists else `main`.
- Work branch MUST be `impl/<slug>`.
- PRIMARY verifies current branch and switches/creates as needed.

---

## DISCOVERY PHASE (mandatory before any fan-out)

Purpose: determine file ownership deterministically and avoid chicken-and-egg.

For each chosen TaskID:
1) Read the Task definition in TASKS.md (full block).
2) Do minimal repo inspection (read-only) to identify what must change to satisfy Done condition.
3) Produce a Proposed File Touch Set per TaskID:
   - MUST TOUCH: exact paths required
   - MAY TOUCH: paths that might be needed if unavoidable
4) Decide parallelism:
   - If ANY overlap between touch sets (including “MAY TOUCH”): SERIALIZE (no sub-agents).
   - Only if STRICTLY file-disjoint: parallelize allowed.

---

## SUB-AGENT AVAILABILITY & WAIT SAFETY (hard)

This prevents “Waiting for agents … agents: none” loops.

- PRIMARY may attempt fan-out at most ONCE per run.
- READY GATE:
  - PRIMARY MUST NOT enter “Waiting for agents” unless each spawned sub-agent reports a ready/initialized state.
  - If any spawned agent remains `pending init` (or equivalent) after a single check, PRIMARY MUST disable fan-out and continue PRIMARY-only.
- FAIL-FAST:
  - If any wait returns `agents: none`, PRIMARY MUST immediately abort fan-out, record “sub-agents unavailable” in report, and continue serialized PRIMARY-only.
  - PRIMARY MUST NOT retry waiting loops in this run.

---

## FAN-OUT / FAN-IN OPERATING MODEL
(Only if discovery proves file-disjoint AND sub-agents are available per safety rules)

### Fan-out
- PRIMARY chooses up to 2 TaskIDs for this chunk (per scope discipline).
- PRIMARY creates one sub-agent per TaskID (max 2).
- PRIMARY assigns explicit, minimal file lists (from Discovery).
- Each sub-agent returns:
  A) brief analysis of changes needed
  B) file list (must match assigned list)
  C) unified diff patches (minimal, reviewable)
  D) verification commands relevant to the task (no docs changes)
  E) risks/edge cases
- If sub-agent detects spec/task ambiguity: STOP and report ambiguity only (no patch).

### Patch handling rule (mandatory)
- Sub-agent diffs are ADVISORY.
- PRIMARY MUST review logically against SPEC/TASKS/ACCEPTANCE.
- PRIMARY MUST NOT “apply blindly”; may implement changes manually.

### Fan-in (PRIMARY sequential)
For each TaskID:
1) Validate patch vs Done condition + constraints
2) Apply/implement patch (PRIMARY-only)
3) Run minimal verification per ACCEPTANCE scoped to that task
4) Run `/review` pre-commit (advisory; fix only if minimal + in-scope; at most one re-run after fix)
5) Atomic commit for that task only (format enforced)
6) Repeat for next task (if any)

---

## NO-COLLISION FILE OWNERSHIP RULE (mandatory)
- PRIMARY must assign non-overlapping file sets to sub-agents.
- If overlap risk exists: DO NOT parallelize—serialize.
- Sub-agents must not modify files outside assigned list.

---

## SUB-AGENT BRIEF TEMPLATE (PRIMARY must paste to each sub-agent)

---
You are SubAgent_<TaskID>. You work ONLY on TaskID: <TaskID> from docs/specs/<slug>/TASKS.md.

Hard rules:
- Do NOT run git commit/push/merge/checkout.
- Do NOT update SPEC/PLAN/TASKS/ACCEPTANCE/CHECKPOINT.
- Do NOT change other tasks. Do NOT refactor unrelated code.
- Touch ONLY these files (no others): <explicit_paths_list>.

Deliverables:
1) Intent (2–4 bullets): what to change to satisfy Done condition.
2) Files: exact paths changed (must equal assigned list).
3) Patch: unified diff (git-style), minimal.
4) Verification: exact commands + expected signals.
5) Risks/Edge cases.

If you detect spec/task ambiguity: STOP and report the ambiguity only (no patch, no extra suggestions).
---

---

## PRIMARY EXECUTION STEPS (enforce)

### Step A — Read/validate contract and summarize (5–8 bullets)
Include:
- what must be built / must not be built
- key constraints
- execution status + current task(s)
- task(s) to implement this chunk

### Step B — Select tasks (max 2)
- If any ambiguity in task fields or acceptance mapping: HARD-STOP.

### Step C — Discovery phase → decide parallelize vs serialize
- Produce touch sets and decide.
- If not strictly disjoint: serialize.

### Step D — Spawn sub-agents only if allowed
- Include explicit file lists.
- Apply sub-agent availability & wait safety rules.

### Step E — PRIMARY prep (safe)
- Ensure `.venv/` / lockfile rules per skill
- Locate relevant code areas
- Draft verification plan aligned with ACCEPTANCE

### Step F — Integrate sequentially (one TaskID at a time)
F1) Validate vs Done condition + constraints  
F2) Implement patch (PRIMARY-only)  
F3) Run minimal verification  

F3.5) Pre-commit review (mandatory for every TaskID)
- Run Codex CLI command: `/review`
- Treat output as **advisory** and classify findings:
  - **Bug / correctness issue** (must fix if minimal + in-scope)
  - **Test gap** (add/adjust tests only if required by ACCEPTANCE)
  - **Style / refactor / nice-to-have** (IGNORE unless required by SPEC/ACCEPTANCE)
- If `/review` reports a **real bug**:
  - Implement the minimal fix (PRIMARY-only; no scope creep).
  - Run the relevant verification.
  - Re-run `/review` at most ONCE after the fix (no loops).

F4) Atomic commit:
`<type>(<slug>): <TaskID> <short title>`  
F5) Record outcomes (pass/fail) and deviations

### Step G — End-of-chunk resume anchor (mandatory)
- Update TASKS.md `## Execution status` (Status/Current task/Last updated/Progress)
- Update or create CHECKPOINT.md (10–25 lines, safe resume)
- Commit docs update:
`docs(<slug>): update execution status after <TaskID(s)>`

### Step H — Push (mandatory)
- Push branch. If push fails: STOP and report the error.

### Conditional Gate — End-of-flow review prompt (only if workflow complete)

**Run condition (deterministic):** ONLY enter this gate if the workflow is complete after this chunk AND at least one high-risk signal holds:
High-risk signals:
- Implemented 2 TaskIDs in this chunk, OR
- Any `/review`-triggered fix was required during Step F, OR
- Touch set included system wiring (routing/config/DI/build/deps).

Consider it complete if either:
- a fresh recompute AFTER Step G (re-read TASKS.md) yields `Remaining: 0`, OR
- TASKS.md indicates there is no next TaskID (all tasks done).

If run condition holds:
1) Announce completion state with evidence:
   - Report `Remaining: 0` (or "no next TaskID") and the recompute method used (from Step G re-read).

2) Do NOT run an additional `/review` automatically. Ask the user (verbatim):

   **Exact question (must use verbatim):**
   `Workflow complete (Remaining: 0). Choose: (A) run /review now, or (B) switch model then run /review. Reply A or B.`

3) Fallback (mandatory, no waiting loops):
   - If the user does NOT reply with exactly `A` or `B` in this run:
     - Skip `/review` entirely.
     - Proceed directly to **Step I — Report**, and include:
       - `Skipped /review: awaiting user choice (A/B).`

4) If the user chooses **A)**:
   - Run Codex CLI command: `/review`

5) If the user chooses **B)**:
   - Ask which model to use (or present 2–3 suggested options if the environment supports switching).
   - Switch as instructed.
   - Then run `/review`.

6) After `/review` is run (via A or B), treat output as **advisory** and classify findings:
   - **Bug / correctness issue** (must fix if minimal + in-scope)
   - **Test gap** (add/adjust tests only if required by ACCEPTANCE)
   - **Style / refactor / nice-to-have** (IGNORE unless required by SPEC/ACCEPTANCE)

7) If `/review` reports a **real bug**:
   - Implement the minimal fix (PRIMARY-only; no scope creep).
   - Run the relevant verification.
   - Atomic commit:
     - `fix(<slug>): review <short description>`
   - If this changes any resume-anchor facts, update TASKS/CHECKPOINT and commit:
     - `docs(<slug>): update execution status after review fix`
   - After any fix/docs commits, re-read TASKS.md once to ensure resume-anchor remains consistent.

8) Re-run `/review` at most ONCE if a fix was made (no loops).
9) If any commits were created in this gate (fix and/or docs), run `git push` again (PRIMARY-only). If push fails: STOP and report the error.

If run condition does NOT hold:
- Skip this gate entirely.

### Step I — Report (concise + factual; include verifiable git facts)
Include:
- TASKS progress done/total
- Current task (before) and next task (after; if Remaining=0, report "none / completed")
- Branch: `impl/<slug>`
- Commits (hash + message)
- Files changed (path → reason)
- Verification commands + results
- CHECKPOINT summary (1–3 bullets)
- Sub-agent status:
  - used/not used
  - if failed: “agents: none” / “pending init” → degraded to PRIMARY-only
- `/review`:
  - run/not run (and why, based on Remaining)
  - findings summary
  - fixes applied (commit hashes) if any
- Deviations: only if SPEC Changelog updated (PRIMARY-only)

---

## PATCH FORMAT REQUIREMENT (sub-agents)
- Use unified diff blocks starting with:
  `diff --git a/<path> b/<path>`
- Minimal context lines.
- If creating new files, include full file content in diff.

---

## IMPORTANT: This run MUST end with a clean “resume anchor”
- CHECKPOINT.md updated (or created)
- TASKS Execution status updated
- push succeeded

Now execute implement-from-spec-git for `<slug>` following this orchestration model.
If `<slug>` is not provided, infer it deterministically using ACTIVE_SLUG rule; STOP if ambiguous.