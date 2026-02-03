---
name: ui-spec-interview
description: UI/Web spec-driven interview. Produces docs/specs/<slug> SPEC/PLAN/TASKS/ACCEPTANCE for browser-based frontend work (screens, components, responsive behavior, accessibility, UX states). NOT for backend or infrastructure. No code.
metadata:
  short-description: UI interview → SPEC/PLAN/TASKS/ACCEPTANCE (screens/components/responsive/a11y). No code.
---


# Purpose

Turn an incomplete or vague **frontend / web UI** idea into a complete, decision-backed design spec, then derive:
1) a high-level `PLAN.md`
2) an atomic `TASKS.md` breakdown (small + reviewable chunks)
3) `ACCEPTANCE.md` criteria (web-focused)

This skill is **spec-driven**:
- You MUST interview first
- You MUST avoid assumptions
- You MUST only generate docs (SPEC/PLAN/TASKS/ACCEPTANCE)
- You MUST NOT implement code

This skill is also **spec-anchored**:
- The SPEC is a living contract
- If implementation later forces changes, the SPEC must be updated and the change logged

---

# Inputs you may receive

- A UI/feature idea described in chat
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
- Suggest a short kebab-case slug (e.g., `pricing-page-revamp`, `admin-dashboard-v2`).

**Frontend + Backend split rule (mandatory)**
If the user says the project includes both frontend and backend:
- You MUST propose 2 slugs:
  - `<base>-frontend`
  - `<base>-backend`
- In THIS skill, proceed ONLY with `<base>-frontend`
- The backend spec can be handled by the existing backend flow

Once `<slug>` is known, set:
- SPEC path = `docs/specs/<slug>/SPEC.md`

If a SPEC file exists, read it first and continue from what is already written:
- Do NOT re-ask answered questions
- Do NOT overwrite existing decisions without explicit user change

---

## Step 0.A — Spec size guardrails (mandatory, early)

You MUST actively prevent “RFC-size specs”.

### Guardrails rule (hard)
If the spec contains either:
- **> 3 major user flows**, OR
- **> 10 acceptance criteria**, OR
- **> 6 distinct screens/routes**
then you MUST propose splitting into **2 specs**.

### What counts as a “major user flow”
A flow is major if it includes its own:
- entrypoint (screen/trigger)
- branching states
- failure states
- distinct user goal

Examples: “Onboarding”, “Checkout”, “Upload & Review”, “Search & Filter + Detail view”.

### Required behavior when guardrail triggers
You MUST:
1) explicitly warn about context/performance risk
2) propose a split plan (two slugs)
3) list what goes into Spec A vs Spec B
4) ask the user to choose:
   - A) split now
   - B) keep single spec (but enforce concision + strict boundaries)

---

## Step 1 — Interview loop (NO coding)

### Objective
Ask high-signal frontend questions until **Open Questions** becomes empty and all critical decisions are made (or explicitly deferred with consequences documented).

### Interview structure rules
- Ask **6–10 questions per round**
- Prefer **multiple-choice (A/B/C/D)** and ALWAYS include:
  - `E) Other: <free text>`
  - `F) Not sure / decide later` (ONLY if truly acceptable to defer)

### Decision-support options (built-in “Help Mode”)
Every question MUST also include meta-options:

- `G) Explain options (A–D)`  
  Provide plain-language explanation for each option + pros/cons.

- `H) Compare options`  
  Compare specific options the user names (e.g., A vs C, or A vs C vs D) using a fixed rubric.

- `I) Recommend`  
  Recommend the best option given current constraints, and explicitly list what info is missing to be confident.

- `J) Show examples`  
  Give small concrete examples (UI structure, component contracts, pseudo-layout), without writing implementation code.

**Important gating rule:**  
If the user answers `G/H/I/J` for any question:
1) You MUST provide the requested explanation/comparison/recommendation/examples
2) Then you MUST re-ask the SAME question (same A–F options)
3) You MUST NOT advance until the user picks A–F (or explicitly defers with F)

---

### Answer format requirement (strict)

Require answers in **ONE single line**, using comma-separated pairs.

Valid examples:
- `Q1=A, Q2=D, Q3=C`
- `Q1=E: <text>, Q2=F, Q3=B`
- `Q1=H: A vs C, Q2=A, Q3=D`

Hard rules:
- One line only (no newlines)
- Items separated by commas
- Letter choices case-insensitive
- For `E) Other`: `Qn=E: <free text>`

If the user does not comply:
- Ask them to resend using the exact format

---

## Step 1A — Frontend constraints-first ordering (mandatory)

In the first round(s), prioritize constraints before stack nitpicks. Ask about:

- target users + context of use
- devices and responsive priorities
- performance expectations (speed, “heavy” UI vs simple)
- accessibility expectations (baseline vs strict)
- SEO needs (marketing page vs app UI)
- data sources (static / API / realtime)
- authentication / roles (if relevant)
- design direction preferences (bold vs minimal, etc.)
- hosting/runtime constraints (Next/Vite, edge, static export)

---

## Step 1B — Option briefs (mandatory)

When you provide A–D options, each option MUST include:

- **What it is (1 line)**
- **When to use (1 line)**

---

## Step 1C — Unknown term detector (mandatory)

If any option includes a term/technology/concept not previously introduced:
- include a 1–2 line definition inline, OR
- encourage `G) Explain options`

Also maintain a short **Glossary** section in SPEC.md for new terms introduced.

---

## Step 1D — Comparison rubric (fixed, consistent)

When the user asks `H) Compare`, you MUST use this rubric:

1) Implementation complexity  
2) UX flexibility / iteration speed  
3) Accessibility impact  
4) Performance impact  
5) Maintainability / scaling  
6) Fit with constraints (stack/team)  
7) Testing story (unit + smoke/E2E)  
8) Edge-case risk (states, loading, errors)

End with:
- “If your #1 priority is X → choose …”
- “If your #1 priority is Y → choose …”
- unknowns that would change the recommendation

---

## Step 1E — Deferral guardrails (“F) decide later”)

Deferral is allowed, but must be managed.

If the user picks `F` for a critical decision:
- add it to **Open Questions** with a clear label
- describe the consequence of deferring (what becomes blocked)
- add a “Default if not decided” fallback ONLY if safe (marked provisional)

---

# Frontend interview question bank (what you MUST cover)

Across the interview, you MUST lock in decisions for:

## Product / UX fundamentals
- Who is the user?
- Primary goal (“happy path”)
- Key screens/routes (limit)
- Navigation model (sidebar/topbar/tabs/single-page flow)
- Empty/loading/error states behavior
- Forms and validation expectations (if relevant)

## Visual direction
- Design tone (minimal/editorial/brutalist/playful/luxury/etc.)
- Brand constraints (existing palette/fonts vs fresh direction)
- Motion preference (none/subtle/hero moments)
- Density preference (spacious vs compact)

## Technical frontend constraints
- Framework/runtime (Next.js/Vite/React/etc.)
- Styling approach (Tailwind/CSS Modules/etc.)
- Component strategy (design system? shadcn? custom?)
- Data fetching model (server vs client vs hybrid)
- Browser support targets
- Accessibility baseline (required)
- Performance posture (strict vs normal)

## Testing / validation
- Smoke validation approach (Playwright recommended)
- “Browser smoke” acceptance

---

# Step 2 — Update SPEC.md continuously (no code)

After each round (or when decisions are made), update `SPEC.md` with:
- clarified requirements
- constraints
- flows/screens (keep concise)
- decisions + rationale
- updated Open Questions
- glossary entries

---

## Mandatory SPEC structure (frontend-focused)

SPEC.md MUST contain these sections:

1) **Summary**
2) **Goals / Non-goals**
3) **Users & Context**
4) **Constraints**
5) **Information Architecture**
   - Screens/routes (numbered)
   - Navigation model
6) **UI/UX Requirements**
   - Key components list
   - Interaction model (keyboard/touch/hover)
   - Responsive behavior (mobile/tablet/desktop)
   - States: loading/empty/error
   - Forms & validation (if any)
7) **Visual Direction**
   - Tone/theme
   - Typography direction
   - Color system direction
   - Motion rules (+ reduced motion)
8) **Frontend Technical Design**
   - Framework + styling choice
   - State/data approach (high-level)
   - Component architecture (high-level)
9) **Edge cases & Failure modes**
10) **Observability (frontend)**
   - error boundaries (conceptually)
   - logging/analytics events (if needed)
11) **Security / Privacy (frontend)**
   - auth assumptions
   - data exposure risks (high-level)
12) **Open Questions**
13) **Decision Log**
14) **Changelog**
15) **Glossary**

---

## Decision logging (mandatory)

Every resolved question must be captured in SPEC.md as:

- **Decision:** <what was chosen>  
- **Rationale:** 1–3 bullets tied to constraints  
- **Risks / mitigations:** (when relevant)

---

## Spec-anchored contract (mandatory)

You MUST add this statement into SPEC.md (verbatim):

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

---

# Step 3 — Generate PLAN.md (no code)

Only after Open Questions is empty (or explicitly deferred with guardrails), generate `PLAN.md`:
- milestones
- phases (UI foundations → screens → polish → testing)
- dependencies/prerequisites
- rollout / rollback approach (basic)
- test strategy (smoke/E2E minimal)

No implementation code.

PLAN.md must remain **high-level**, not a checklist.

---

# Step 4 — Generate TASKS.md (atomic tasks, mandatory)

Convert the PLAN into **atomic, reviewable tasks**.

### Definition: “atomic frontend task”
Atomic if:
- small enough to implement in one sitting
- independently verifiable in the browser
- clear inputs/outputs
- minimal coupling
- tight done condition

### Hard rules for TASKS.md
- Tasks MUST be ordered
- Tasks MUST be grouped by phase
- Each task MUST include:
  - Goal
  - Inputs
  - Outputs
  - Steps (tiny)
  - Done condition
  - Dependencies
  - Risks
  - Test/Verification

Prefer **6–14 tasks total**.

If tasks exceed ~14:
- propose splitting the spec (guardrails)

---

## TASKS.md format (mandatory)

Use this exact structure:

# TASKS

## Phase 0 — Setup / scaffolding
- T0.1 <task title>
  - Goal:
  - Inputs:
  - Outputs:
  - Steps:
  - Done condition:
  - Dependencies:
  - Risks:
  - Test/Verification:

## Phase 1 — UI foundations (tokens, layout, primitives)
(Generated tasks will appear here as T1.x)

## Phase 2 — Core screens / flows
(Generated tasks will appear here as T2.x)

## Phase 3 — States + edge cases (loading/empty/error)
(Generated tasks will appear here as T3.x)

## Phase 4 — Accessibility + performance pass
(Generated tasks will appear here as T4.x)

## Phase 5 — Testing / smoke validation + release readiness
(Generated tasks will appear here as T5.x)

---

## Chunking rule (mandatory)

In `TASKS.md`, after listing all phases and tasks, you MUST include a `Chunking guidance` section containing:

- **Suggested implementation chunk size:** 1–2 tasks per chunk
- **Review cadence:** after each chunk, verify acceptance criteria impacted by those tasks
- **Stop points:** “safe to stop here” markers after phases

---

## Execution status block (mandatory)

At the very end of `TASKS.md`, you MUST include an `Execution status` section.

This section MUST be the last section in the file.

Initial value requirement (mandatory):
When generating `TASKS.md` for the first time, initialize exactly:

## Execution status
- Status: NOT_STARTED
- Current task: T0.1
- Completed tasks: (optional)
- Last updated: YYYY-MM-DD

---

# Step 5 — Generate ACCEPTANCE.md (no code)

Generate acceptance criteria:
- functional happy-path (1–2)
- edge cases (1–2)
- responsive behavior (1)
- accessibility baseline (1)
- performance posture (optional, keep light)
- browser smoke / Playwright smoke (1)

Soft target: **6–10 criteria**.

---

## Web baseline acceptance (mandatory)

ACCEPTANCE.md MUST include:

## A0 — Browser smoke (web)
- The app loads in Chromium without critical console errors.
- The primary happy-path flow works end-to-end in the browser.

Notes:
- Keep A0 minimal (smoke only).
- Do NOT require a full E2E suite unless scope demands it.

---

# Output discipline

- Do not create any files other than SPEC/PLAN/TASKS/ACCEPTANCE under the target folder.
- Do not implement code.
- Do not assume stack choices without asking (or documenting defaults).
- Keep the spec concise and enforce guardrails.
