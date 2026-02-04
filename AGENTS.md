## Design & workflow policy

- For any task involving non-trivial design, trade-offs, or architecture:
  - Use the `spec-interview` skill first.
  - Do NOT implement code until SPEC.md has no Open Questions.

- Small, local, or mechanical changes may skip the spec workflow unless explicitly requested.

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