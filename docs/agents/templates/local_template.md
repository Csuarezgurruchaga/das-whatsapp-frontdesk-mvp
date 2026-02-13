# AGENTS (Local Project Log)

> **Purpose**: High-signal, append-only log for this repository.  
> **Audience**: Humans and coding agents resuming work after context loss.  
> **Compliance**: Follows global workflow in `$HOME/.codex/AGENTS.md`

**Quick nav**: [Context](#0-quick-context) | [Decisions](#1-decisions) | [Fixes](#2-incidents--fixes) | [Commands](#3-commands) | [Pitfalls](#4-pitfalls) | [TODOs](#5-open-questions--todo)

---

## 0) Quick context

- Project: <name>
- Repo root: <path or URL>
- Stack: <e.g., Python 3.11, FastAPI, Postgres>
- Run: `<command>`
- Test: `<command>`
- Status: <1-line current work>

---

## 1) Decisions

**Format**: `YYYY-MM-DD — <title> [D-###]`
- Context: <why>
- Decision: <what>
- Alternatives: <other options>
- Consequences: <trade-offs>

<details><summary>Example</summary>

- 2026-01-15 — Switch to Redis for sessions [D-001]
  - Context: PG session table at 50GB, slow queries
  - Decision: Redis with 24h TTL
  - Alternatives: Partition PG table, in-memory (no persistence)
  - Consequences: +Redis dependency, -99% query time

</details>

**For breaking changes**: Add `[BREAKING]` tag after ID, include:
- **Migration steps**: numbered list with commands
- **Rollback plan**: how to undo if it breaks

Example:
- 2026-01-28 — Migrate to PostgreSQL [D-003] [BREAKING]
  - Context: SQLite locking issues
  - Decision: PostgreSQL 15
  - **Migration steps**:
    1. `brew install postgresql@15`
    2. `createdb myapp_dev`
    3. Run `alembic upgrade head`
  - **Rollback plan**: Restore .env, rebuild from backup.sql
  - Consequences: +ops overhead, +100x throughput

---

## 2) Incidents & Fixes

**Format**: `YYYY-MM-DD — <title> [F-###] [AGENT?]`
- Area: <file/component>
- Symptom: <what happened>
- Root cause: <why> (or `unknown`)
- Fix: <what changed>
- Proof: <test/command>

<details><summary>Example</summary>

- 2026-01-20 — Auth crashes on bad JWT [F-001]
  - Area: src/auth/middleware.py:45
  - Symptom: 500 on "Bearer <garbage>"
  - Root cause: Unhandled InvalidTokenError
  - Fix: try/except, return 401
  - Proof: `pytest tests/auth/test_malformed_tokens.py`

</details>

---

## 3) Commands

**Format**: `YYYY-MM-DD — <what it does> [C-###]`
- Command: `<paste>`
- Expected: <success looks like>
- Notes: <gotchas>

<details><summary>Example</summary>

- 2026-01-18 — Run tests with coverage [C-001]
  - Command: `docker-compose run --rm api pytest --cov=src`
  - Expected: Coverage report in htmlcov/
  - Notes: Requires Docker running

</details>

---

## 4) Pitfalls

**Format**: `YYYY-MM-DD — <constraint> [P-###]`
- What: <the problem>
- Why it matters: <impact>
- How to avoid: <solution>

<details><summary>Example</summary>

- 2026-01-22 — PG max_connections in CI [P-001]
  - What: Random "too many clients" failures
  - Why: Blocks PRs
  - How to avoid: Use pgbouncer or max_connections=200

</details>

---

## 5) Open questions / TODO

**Format**: `YYYY-MM-DD — <question> [T-###]`
- Notes: <context>

<details><summary>Example</summary>

- 2026-01-25 — Support Python 3.9? [T-001]
  - Notes: Code uses tomllib (3.11+). Check user base.

</details>

---

## 6) Agent logging triggers

Log when:
- Bug fixed + test added -> [F-###]
- Architecture decision made -> [D-###]
- Command used 3+ times -> [C-###]
- Error took >30min to debug -> [F-###] or [P-###]
- Dependency added/removed -> [D-###]
- Agent made a wrong assumption / broke something / had to backtrack -> [F-###] [AGENT]

**IDs**: D-001, F-001, C-001, P-001, T-001 (increment per section)

**End of session checklist**:
1. Review changes: files modified, tests added, errors debugged
2. Add entries if: bug fixed, decision made, command repeated 3+, pitfall found
3. Update section 0 "Status" (1 line max)
4. Verify all entries have proof/references when applicable
