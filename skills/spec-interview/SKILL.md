---
name: spec-interview
description: Interview the user to complete a SPEC.md, then generate PLAN.md, TASKS.md and ACCEPTANCE.md. Use multiple-choice questions with built-in explain/compare/recommend helpers. Do not write code until the spec is complete.
metadata:
  short-description: Spec-driven interview → SPEC/PLAN/TASKS/ACCEPTANCE (atomic tasks + size guardrails + spec-anchored)
---

# Purpose

Turn an incomplete or vague idea into a complete, decision-backed design spec, then derive:
1) a high-level PLAN
2) an atomic TASK breakdown (small + reviewable chunks)
3) acceptance criteria

This skill is **spec-driven**:
- You MUST interview first.
- You MUST avoid assumptions.
- You MUST only generate docs (SPEC/PLAN/TASKS/ACCEPTANCE). Do not implement code.

This skill is also **spec-anchored**:
- The SPEC is a living contract.
- If implementation later forces changes, the SPEC must be updated and the change logged.

---

# Inputs you may receive

- A feature idea described in chat
- An existing draft at `docs/specs/<slug>/SPEC.md` (may be empty or partial)
- A requested `<slug>` (optional)

---

# Outputs (must be created/updated)

Create or update exactly these files:

- `docs/specs/<slug>/SPEC.md`
- `docs/specs/<slug>/PLAN.md`
- `docs/specs/<slug>/TASKS.md`
- `docs/specs/<slug>/ACCEPTANCE.md`

Also create the directory if missing:
- `docs/specs/<slug>/`

---

# Strict workflow

## Step 0 — Identify the spec slug

If the user did not provide `<slug>`, ask for it.
- Suggest a short kebab-case slug (e.g., `invoice-email-classifier`).

Once `<slug>` is known, set:
- SPEC path = `docs/specs/<slug>/SPEC.md`

If a SPEC file exists, read it first and continue from what is already written.
- Do NOT re-ask answered questions.
- Do NOT overwrite existing decisions without explicit user change.

---

## Step 0.A — Spec size guardrails (mandatory, early)

You MUST actively prevent “RFC-size specs”.

### Guardrails rule (hard)
If the spec contains either:
- **> 3 major flows** (large user/system workflows), OR
- **> 10 acceptance criteria**
then you MUST propose splitting into **2 specs**.

### What counts as a “major flow”
A flow is “major” if it includes its own:
- trigger/entrypoint
- branching logic / states
- failure modes
- different actor/system boundaries

Examples: “Ingest → Validate → Persist”, “Checkout → Payment → Confirmation”, “Upload → OCR → Review”.

### Required behavior when guardrail triggers
You MUST:
1) explicitly warn about context/performance risk
2) propose a split plan (two slugs)
3) list what goes into Spec A vs Spec B
4) ask the user to choose:
   - A) split now
   - B) keep single spec (but you must enforce concision and “phase boundaries”)


## Step 0B — Split output rule (mandatory)

If splitting into multiple specs is chosen, you MUST enforce a clean folder-per-spec layout:

- Create **one folder per spec**:
  - `docs/specs/<slug-a>/`
  - `docs/specs/<slug-b>/`

- Each spec folder MUST contain the **full set of files**:
  - `SPEC.md`
  - `PLAN.md`
  - `TASKS.md`
  - `ACCEPTANCE.md`

- Do NOT create alternate spec filenames such as:
  - `SPEC-part2.md`
  - `SPEC_v2.md`
  - `SPEC (copy).md`

### Session safety rule (mandatory)

Splitting into multiple specs can still overflow context if you attempt to fully write everything at once.

Therefore:
- Unless the user explicitly requests otherwise, you MUST generate **only one complete spec package** per session:
  - `SPEC.md`
  - `PLAN.md`
  - `TASKS.md`
  - `ACCEPTANCE.md`

For the second spec (`<slug-b>`), you MUST create ONLY a lightweight draft `SPEC.md` containing:
- Summary
- Goals / Non-goals (high-level)
- Scope boundary (what is excluded from Spec A)
- Dependencies (explicitly reference Spec A)
- Open Questions

You MUST NOT generate `PLAN.md`, `TASKS.md`, or `ACCEPTANCE.md` for `<slug-b>` in the same session unless the user explicitly asks for it.

---

## Step 1 — Interview loop (NO coding)

### Objective

Ask high-signal, non-obvious questions until **Open Questions** becomes empty and all critical decisions are made (or explicitly deferred with documented consequences).

### Interview structure rules

- Ask **2–10 questions per round** (default 6–10; early rounds may be shorter, e.g., Q0–Q1).
- Prefer **multiple-choice (A/B/C/D)** and ALWAYS include as mandatory:
  - `E) Other: <free text>`
  - `F) Not sure / decide later` (ONLY if truly acceptable to defer)

## Step 1 — Render Format Rules (HARD, ALWAYS)

You MUST ALWAYS render interview questions in the exact **“ronda spec-interview”** format:

### 1) Round header (mandatory)
At the start of each round, print:

- `## Ronda N (Qx–Qy)`

where `N` is the round number and `Qx–Qy` is the inclusive range of questions in this round.

### 2) Per-question header (mandatory)
Each question MUST start with exactly:

- `Q0 — <título>`
- `Q1 — <título>`
- etc.

### 3) Options formatting (mandatory)
Each question MUST include options on separate lines with this exact prefixing:

- `A) ...`
- `B) ...`
- (optional `C) ...`, `D) ...`)
- `E) Other: <texto>`
- `F) Not sure / decide later`

Rules:
- You may include **A–D** as needed (2–4 choices), but **E and F are ALWAYS required**.
- If deferral is truly not acceptable, you MUST still show `F)` but annotate it, e.g.:
  - `F) Not sure / decide later (allowed, but blocks PLAN/TASKS until resolved)`

### 4) Meta-options single-line rule (mandatory)
After the A–F lines, you MUST include meta-options in **one single line** exactly:

- `G) Explain options, H) Compare, I) Recommend, J) Show examples`

### 5) End-of-round answer instruction (mandatory)
At the end of the round, you MUST instruct the user:

- `Responde en UNA sola línea con pares separados por comas: Q0=..., Q1=..., ...`

And you MUST clarify the free-text case:

- `Para texto libre: Q0=E: <tu-texto>`

You MUST also include a short exact example (minimum):

- `Ejemplo: Q0=E: voice-agent-mvp, Q1=A`

### Answer format requirement (strict)

At the end of each round, you MUST require answers in **ONE single line**, using comma-separated pairs: `Qn=...`.

**Valid format (case-insensitive):**
- `Q1=A, Q2=D, Q3=C`
- `q1=a, q2=d, q3=c`
- `Q1=E: <text>, Q2=F, Q3=B`

**Hard rules**
- All answers MUST be in **one line** only (no newlines).
- Items MUST be separated by commas `,`
- A space after comma is optional: `Q1=A,Q2=B` is valid.
- Letter choices are **case-insensitive** (A/a are equivalent).
- For `E) Other`, the format MUST be: `Qn=E: <free text>`
- For meta-options, the format MUST be: `Qn=G` or `Qn=H: A vs C` etc.

If the user does not comply, politely ask them to resend using the exact format.

## Step 1A — Constraints-first ordering (reduce confusion)

In the first round(s), prioritize constraints before proposing “stack” choices. Ask about:
- scale/throughput, latency, availability/SLA
- budget/cost sensitivity
- hosting/runtime constraints (Cloud Run? K8s? serverless?)
- data sensitivity/security/privacy/compliance needs
- integration boundaries (existing DB, APIs, auth)
- idempotency/duplication tolerance
- observability requirements

---

## Step 1B — Option briefs (mandatory)

When you provide A–D technical options, each option MUST include a brief:

**Format per option:**
- **What it is (1 line)**
- **When to use (1 line)**

---

## Step 1C — Unknown term detector (mandatory)

If any option includes a term/technology/concept that has NOT appeared in the spec yet (or is niche), you MUST do one of:
- Automatically include a 1–2 line definition inline, OR
- Encourage `G) Explain options`

Additionally, maintain a short **Glossary** section in SPEC.md for new terms introduced.

---

## Step 1D — Comparison rubric (fixed, consistent)

When the user asks `H) Compare`, you MUST use the same rubric every time:

1) Operational complexity  
2) Reliability semantics (retries, DLQ, backoff)  
3) Idempotency & dedupe story  
4) Latency characteristics  
5) Cost drivers  
6) Observability (logs/metrics/tracing)  
7) Vendor lock-in / portability  
8) Edge-case risk (timeouts, concurrency, ordering)

End with:
- “If your #1 priority is X → choose …”
- “If your #1 priority is Y → choose …”
- Any “unknowns” that would change the recommendation

---

## Step 1E — Recommend mode requirements

If the user asks `I) Recommend`, you MUST:
- state the recommendation
- state assumptions (explicitly)
- list missing info (what would change the choice)
- propose 1–2 follow-up questions (but do NOT exceed the 6–10 questions per round overall)

---

## Step 1F — Deferral guardrails (“F) decide later”)

Deferral is allowed, but must be managed:

- If the user picks `F` for a critical decision, you MUST:
  - add it to **Open Questions** with a specific label,
  - describe the consequence of deferring (what in PLAN is blocked or becomes more expensive),
  - add a “Default if not decided” fallback (only if safe), clearly marked as provisional.

---

## Step 2 — Update SPEC.md continuously (no code)

After each round (or when a decision is made), update `SPEC.md` with:
- clarified requirements
- constraints
- flows (keep concise)
- decisions and rationale
- updated Open Questions (remove answered, add new)
- glossary entries for new terms introduced

### Mandatory SPEC structure (enforce)

SPEC.md MUST contain these sections:

1) **Summary**
2) **Goals / Non-goals**
3) **Constraints**
4) **Key Flows** (numbered, keep minimal)
5) **Data / Interfaces** (only what matters)
6) **Edge cases & Failure modes**
7) **Observability**
8) **Security / Privacy**
9) **Open Questions** (must end empty or explicitly deferred w/ consequences)
10) **Decision Log** (living)
11) **Changelog** (living)
12) **Glossary** (short)

### Decision logging (mandatory)

Every resolved question must be captured in SPEC.md as:

- **Decision:** <what was chosen>  
- **Rationale:** 1–3 bullets tied to constraints
- **Risks / mitigations:** (when relevant)

### Changelog (mandatory, spec-anchored)

SPEC.md MUST include a **Changelog** section.
Whenever a change happens later (post-implementation learnings), it should be captured as:

- YYYY-MM-DD — <change summary>
  - reason: <why it changed> (keep concise)
  - impact: <what else must update: tasks/plan/acceptance>

Even though this skill does NOT implement code, it MUST set up the SPEC to support this future update flow.

---

## Step 2A — Enforce “Spec-anchored” contract

You MUST add this statement into SPEC.md (verbatim):

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

---

## Step 3 — Generate PLAN.md (no code)

Only after Open Questions is empty (or explicitly deferred with documented guardrails), generate `PLAN.md`:
- milestones
- tasks grouped by phase
- dependencies and prerequisites
- observability, rollout/rollback plan
- test strategy

No implementation code.

PLAN.md must remain **high-level**, not a checklist.

---

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

---

## Step 5 — Generate ACCEPTANCE.md (no code)

### Web app baseline acceptance (mandatory)

If the product includes a web UI (frontend / browser-based app), you MUST include this baseline criterion in ACCEPTANCE.md:

## A0 — Browser smoke (web)
- The app loads in Chromium without critical console errors.
- The primary happy-path flow works end-to-end in the browser.

Notes:
- Keep A0 minimal (smoke only).
- Do NOT add a full E2E test suite unless explicitly required by scope.

Generate acceptance criteria:
- functional acceptance tests (happy path + edge cases)
- non-functional criteria (latency, reliability, cost ceilings if provided)
- observability checks
- security/privacy checks
- rollback criteria

No implementation code.

### Acceptance size guardrail (scope vs quality)

ACCEPTANCE.md should remain small enough to be usable during chunked implementation.

**Soft limit:** aim for 6–10 criteria total.

If ACCEPTANCE.md exceeds **10 criteria**, you MUST do this in order:

1) **Normalize (mandatory):**
   - Merge redundant criteria.
   - Group by category:
     - Functional (happy path)
     - Edge cases / failure modes
     - Non-functional (latency, cost, reliability)
     - Observability
     - Security/Privacy
   - Prefer fewer, stronger criteria over many tiny ones.

2) **Split decision (only if scope indicates it):**
   Propose splitting into 2 specs ONLY if at least one is true:
   - The spec has **> 3 major flows**, OR
   - Criteria naturally split into **2 independent deliverables** (e.g., "core feature" vs "admin/backoffice"), OR
   - There are **multiple integration boundaries** that can ship independently.

If split is triggered:
- Propose Spec A (core value) + Spec B (extensions/hardening/integrations)
- Move acceptance criteria accordingly.

---

# Interview question quality guidelines

Avoid obvious questions. Favor:
- failure modes & edge cases
- rollout/rollback strategy
- rate limits, retries, concurrency, ordering
- idempotency & deduplication
- data ownership & retention
- security/privacy/compliance implications
- observability & SLOs
- migration/backward compatibility constraints
- cost drivers & quotas

---

# Output discipline

- Do not create any files other than SPEC.md, PLAN.md, TASKS.md, ACCEPTANCE.md in the target folder.
- Do not implement code.
- Do not propose “final architecture” until constraints are captured.
- When uncertain, ask; do not assume.

