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
