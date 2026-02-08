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
