## Design & workflow policy

## Pre-flight checklist (execute before any code changes)

Before modifying code in any project:

- [ ] **Local AGENTS.md exists**
  - Path: `<repo_root>/AGENTS.md`
  - If missing: `cp $HOME/.codex/templates/agents_local.md <repo_root>/AGENTS.md`
  - Action: Read it fully before proceeding

- [ ] **Understand the scope**
  - Is this trivial/mechanical? (single file, <20 lines, no architecture impact)
  - Is this non-trivial? (check for existing specs in `docs/specs/`)

- [ ] **Verify test infrastructure**
  - Do tests exist? (run `make test` or equivalent)
  - If NO tests: state this explicitly, do NOT create test infrastructure unless asked

- [ ] **Check for open questions**
  - Review local AGENTS.md section 5 (Open questions/TODO)
  - Review any SPEC.md files in `docs/specs/<slug>/`

**If unsure about any item**: ask before proceeding.

---

- For any task involving non-trivial design, trade-offs, or architecture:
  - Use the `spec-interview` skill first.
  - Do NOT implement code until SPEC.md has no Open Questions.

- **Small/mechanical changes** (MAY skip spec workflow):
  - Single-file edits with <20 lines changed
  - Typo fixes, formatting, linting
  - Dependency version bumps (patch-level only)
  - Log message improvements
  
- **Non-trivial changes** (MUST use spec workflow):
  - Affects >2 files OR >50 lines total
  - Changes public APIs, data models, or schemas
  - Introduces new dependencies or architectural patterns
  - Modifies authentication, authorization, or security logic
  - Changes behavior that users or external systems depend on
  
- **When in doubt**: err on the side of creating a spec. Over-documentation is recoverable; under-documentation causes rework.

- Specs live under `docs/specs/<slug>/` and are the source of truth.

## Implementation principles

- Avoid assumptions. If something is ambiguous, ask.
- Prefer minimal, reviewable diffs.
- Avoid unrelated refactors.
- Ask before:
  - adding dependencies or tools
  - changing public APIs
  - changing data models or schemas

## Verification & safety

- If tests or linters exist, run them and report results.
- If they do not exist, state that clearly (do not add tooling unless asked).
- If a command could modify or delete files, ask before running it.

### Bugfix protocol (default)

- **Rule:** No fix without repro.

When a bug is reported:
1) Create a minimal reproduction that fails (prefer: automated test).
2) Commit the failing repro/test before attempting fixes (use squash/fixup so the final PR history is green-only).
3) Implement the fix.
4) Prove the fix by making the repro/test pass and running the relevant suite.
5) Add regression coverage to prevent recurrence.

**Acceptable proofs (in order):**
- Deterministic automated test (unit/integration/e2e)
- Deterministic repro script/fixture + CI command
- Logged assertion/invariant + controlled repro steps + captured artifacts

**Exceptions (must be stated explicitly in the PR/commit message):**
- Repro requires external systems not available in CI
- Non-deterministic/concurrency issues where a stable test is not feasible
- Emergency hotfix (must be followed by a repro within N days)

## Environment & tooling

- Primary language: Python.
- Prefer clarity over cleverness.
- Never install dependencies globally.
- For Python:
  - Always use a per-project virtual environment (`.venv`).
- Follow existing project conventions (README, Makefile, pyproject, etc.).

## Collaboration (multi-agent safety)

- You are not alone in this environment. Do not impact or overwrite the work of others.
- If multiple agents are used, only the primary (orchestrator) agent should integrate changes.
- Subagents must not propose fixes without also proposing:
  - where the repro/test should live
  - what condition fails pre-fix
  - what command(s) prove the fix

## Output expectations

- Explanations should focus on:
  - key decisions and trade-offs
  - how the system works at a high level
  - how to run and test based on what exists
- Keep explanations concise unless more detail is requested.

## Local AGENTS.md policy (scope, creation, logging)

### Global vs Local AGENTS

- This file (`~/.codex/AGENTS.md`) is **GLOBAL**:
  - Defines workflow rules, safety constraints, and agent behavior.
  - It is NOT a project-specific log or decision record.

- Every project/repository MUST have its own **LOCAL `AGENTS.md`** (at that repo root):
  - Created at project initialization if missing.
  - Used as a persistent development log / ledger.
  - Survives context resets, agent restarts, and squash merges.

### Local AGENTS.md (required)

When starting work on a project/repo:

- If `AGENTS.md` does not exist at the project root:
  - Create it immediately by copying `~/.codex/templates/agents_local.md` to `<repo_root>/AGENTS.md` (verbatim).
- If it exists:
  - Read it before making changes.

If both a GLOBAL and LOCAL AGENTS exist:
- Follow the GLOBAL rules in `~/.codex/AGENTS.md`.
- Write project-specific logs to the LOCAL `<repo_root>/AGENTS.md`.

### Update rules

- Updates are **append-only** by default.
- Do NOT rewrite or delete existing entries unless explicitly instructed.
- Avoid noise: log only information that would help resume work after context loss.
- Each entry should include:
  - date (ISO)
  - context (file/service/component)
  - problem
  - solution
  - optional notes / follow-ups
  - optional proof (command/test/log) when relevant

### Triggers (when to log)

Log an entry when:
- a bug is fixed (especially after a repro/test is added)
- a non-trivial design/architecture decision is made
- environment/infra/CI changes were required to make progress
- you discover a pitfall that could easily waste time again

### Responsibility

- The active coding agent is responsible for:
  - proposing new entries when relevant events occur
  - keeping the local `AGENTS.md` up to date
- If unsure whether something should be logged:
  - prefer logging briefly over omitting it.

# Project Context

This project is configured with Model Context Protocol (MCP) servers that extend Codex's capabilities for GitHub operations and browser automation.

## Available MCP Servers

### Context7 MCP
Provides just-in-time documentation/context retrieval for libraries and frameworks.

**When to use:**
- Confirm APIs, versions, edge cases, or canonical usage
- Validate best practices against official docs before implementing
- Resolve ambiguous framework/SDK behavior to avoid wrong assumptions

**Common tasks:**
- "Check the correct usage of [library/function]"
- "Confirm breaking changes between versions of [library]"
- "Find a minimal example for [framework feature]"

### Playwright MCP
Provides real browser automation for UI verification (navigate, click, fill forms, wait for selectors/URLs, take screenshots).

**When to use:**
- Validate UI changes (routing, layout, CSS, components)
- Reproduce or verify a reported frontend bug
- Smoke-test critical flows (login, submit forms, navigation)
- Capture evidence (screenshots/logs) for PRs or specs

**Common tasks:**
- "Open [URL] and take desktop + mobile screenshots"
- "Verify login redirects to /dashboard"
- "Check main navigation links aren’t broken"
- "Reproduce bug: [steps] and capture screenshots + console errors"

## Work Log

- date: 2026-02-08
- context: `bin/sb-ui`
- problem: `sb-ui` fallaba con `python3: can't open file '/Users/csuarezgurruchaga/dev-tools/.../codex-interview-wrapper.py'` al ejecutarse desde `~/.bin/sb-ui` (symlink), porque la raíz se calculaba desde la ruta del symlink.
- solution: se agregó resolución explícita de symlinks (`readlink` loop) antes de calcular `ROOT_DIR`, de modo que el script siempre derive a `~/.codex/...`.
- proof: `ls -la ~/.bin/sb-ui ~/.codex/bin/sb-ui ~/.codex/dev-tools/spec-interview-ui-wrapper/scripts/codex-interview-wrapper.py` y `python3 ~/.codex/dev-tools/spec-interview-ui-wrapper/scripts/codex-interview-wrapper.py --help`.

- date: 2026-02-05
- context: `skills/spec-interview/scripts/codex-interview-wrapper.py` parser de rondas (Qn/opciones)
- problem: El UI batch mostraba texto basura incrustado en títulos/opciones (ej. `Drafting initial interview questions`, `for shortcuts99% context left`, y fragmentos cortos como `onnss`) por líneas de estado de Codex mezcladas con contenido parseado.
- solution: Se endureció `_strip_inline_chrome` para cortar nuevas variantes de chrome/status y se ajustó `_is_option_continuation_line` para ignorar fragmentos cortos de un solo token que no son continuidad real de opciones.
- notes: Se agregó repro automatizado para la variante observada y se mantuvieron verdes los tests existentes del wrapper.
- proof: `python3 -m unittest -v skills/spec-interview/scripts/tests/test_codex_interview_wrapper.py`

- date: 2026-02-08
- context: `bin/sb-ui` (host vs container path)
- problem: `sb-ui` seguía fallando con `can't open file '/Users/.../.codex/dev-tools/.../codex-interview-wrapper.py'` porque ese path de host se pasaba a `sb` y se intentaba resolver dentro del contenedor.
- solution: `bin/sb-ui` ahora valida `HOST_WRAPPER_PATH` en host y ejecuta dentro de `sb` usando `CONTAINER_WRAPPER_PATH=/root/.codex/dev-tools/spec-interview-ui-wrapper/scripts/codex-interview-wrapper.py`.
- notes: se mantuvo resolución de symlink para localizar correctamente la raíz de `~/.codex` cuando `sb-ui` se invoca desde `~/.bin/sb-ui`.
- proof: `bash -n ~/.codex/bin/sb-ui` y `ls -la ~/.codex/dev-tools/spec-interview-ui-wrapper/scripts/codex-interview-wrapper.py`.
