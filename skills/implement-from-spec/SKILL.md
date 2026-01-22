---
name: implement-from-spec
description: Implement code strictly from an approved SPEC/PLAN/ACCEPTANCE without redesigning or re-questioning decisions.
metadata:
  short-description: Execute implementation from finalized spec
---

# Purpose

Execute an implementation **only** after a design has been finalized.

This skill assumes:
- Design decisions are already made.
- Trade-offs are already resolved.
- The SPEC is the contract.

This skill is **execution-only**.

# Preconditions (MUST enforce)

Before writing any code, you MUST verify:

1) A spec directory exists at:
   - `docs/specs/<slug>/`

2) The following files exist:
   - `SPEC.md`
   - `PLAN.md`
   - `ACCEPTANCE.md`

3) `SPEC.md` contains an "Open Questions" section AND it is empty.

If ANY precondition fails:
- Stop immediately.
- Explain what is missing.
- Do NOT implement anything.

# Inputs

- `<slug>` identifying the spec (required).
- The contents of:
  - `docs/specs/<slug>/SPEC.md`
  - `docs/specs/<slug>/PLAN.md`
  - `docs/specs/<slug>/ACCEPTANCE.md`

# Strict execution rules

- Do NOT redesign.
- Do NOT propose alternatives.
- Do NOT re-open decisions already documented.
- Do NOT add features not explicitly listed.
- Do NOT “improve” the design.
- Do NOT refactor unrelated code.

If something is unclear:
- Check the SPEC first.
- If still unclear, stop and report the ambiguity.
- Do NOT guess.

# Execution workflow

## Step 1 — Load and summarize the contract
- Read SPEC.md, PLAN.md, ACCEPTANCE.md.
- Produce a brief summary (5–7 bullets) of:
  - What must be built
  - What must NOT be built
  - Key constraints

Confirm understanding before proceeding.

## Step 2 — Implementation
- Follow PLAN.md step by step.
- Apply minimal, reviewable diffs.
- Touch only files implied by PLAN.md.
- Preserve existing style and conventions.

## Step 3 — Verification
- Validate against ACCEPTANCE.md.
- If tests exist:
  - Run them and report results.
- If tests do not exist:
  - State that clearly.
  - Do NOT add new tooling unless PLAN.md explicitly says so.

## Step 4 — Report
After implementation, report:

- Files changed (with brief reason per file)
- Acceptance criteria status:
  - Passed / Failed / Not applicable
- Any deviations from PLAN (must be justified)

# Output expectations

- Implementation must match the SPEC and PLAN exactly.
- Explanations should be concise and factual.
- No redesign commentary.
- No speculative improvements.

# Failure mode

If at any point the SPEC is insufficient to implement safely:
- Stop.
- Explain precisely what is missing.
- Recommend returning to `spec-interview`.

This skill values **discipline over creativity**.

