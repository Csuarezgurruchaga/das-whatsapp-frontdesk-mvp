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
