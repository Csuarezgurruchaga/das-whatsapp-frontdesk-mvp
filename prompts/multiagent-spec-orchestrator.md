Use the skill: `$spec-interview <slug>`.

Language policy:
- I may message you in Spanish.
- You MUST follow these operational instructions regardless of language.
- Ask questions and report in Spanish. Keep code/paths/commands/identifiers exactly as written.

Operational rules (best practices):
- Single-writer: ONLY the main thread may edit files, run commands, or touch git.
- Subagents are READ-ONLY: no file edits, no commands, no git.
- Fan-out/Fan-in: parallelize analysis, then consolidate into ONE coherent spec package.
- No assumptions: if something is unclear or missing, ask. Do NOT guess.
- No implementation: do NOT write code in this phase.
- Enforce size guardrails: if >3 major flows OR >10 acceptance criteria, propose splitting into 2 specs (two slugs) before writing everything.

Inputs:
- Slug: OPTIONAL. If missing, propose 1–3 kebab-case slug options and ask me to pick one.
- Context/goal: OPTIONAL / can be rough. If missing, ask clarifying questions.
- Constraints: OPTIONAL. If missing, ask.
- Known assumptions: OPTIONAL.

FAN-OUT (Multi-agents):
Spawn 3 READ-ONLY subagents with strict roles and limits.

Shared input for ALL subagents:
- Context/goal: <1–3 lines>
- Constraints: <stack, “no new deps”, deadlines, compatibility, etc.>
- Known assumptions (if any): <...>

Subagent roles:
1) Scope/Split Police:
   - Identify scope creep, propose splits/phases, and list explicit out-of-scope items.
2) QA/Acceptance Designer:
   - Convert requirements into testable acceptance criteria + a minimal verification plan.
3) Risks/Edge-cases Auditor:
   - Enumerate failure modes, safety/security concerns, performance risks, and rollback considerations.

Subagent output format (MANDATORY, max 12 lines each):
- Findings: (3 bullets)
- Open questions: (up to 3 bullets)
- Recommendation: (1–2 bullets)
- Do-not-do (out of scope): (1–2 bullets)

FAN-IN (Main thread):
1) Wait for all 3 subagents to finish.
2) Consolidate into `docs/specs/<slug>/SPEC.md` (decisions + constraints + flows).
3) Generate `PLAN.md`, `TASKS.md` (atomic tasks; 1–2 tasks per chunk), and `ACCEPTANCE.md`.
4) If any Open Questions remain, ask me in ONE block (prefer multiple-choice + your recommended option).
5) Only when Open Questions are empty, confirm the spec package is ready for implementation.

If subagents cannot be spawned:
- ALERT me explicitly (one short sentence).
- Then continue sequentially as a single agent (skip Fan-out; proceed with Fan-in steps).
- Do NOT claim you used subagents or present “subagent results”.

Now start.

Slug: <slug | omit>
Context/goal: <... | omit>
Constraints: <... | omit>
Known assumptions: <... | omit>
