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

## Output expectations

- Explanations should focus on:
  - key decisions and trade-offs
  - how the system works at a high level
  - how to run and test based on what exists
- Keep explanations concise unless more detail is requested.

# Project Context

This project is configured with Model Context Protocol (MCP) servers that extend Codex's capabilities for GitHub operations and browser automation.

## Available MCP Servers

### GitHub MCP
Provides integration with GitHub repositories and operations.

Always use GitHub username: `csuarezgurruchaga` (display: `@csuarezgurruchaga`).

**When to use:**
- List or search repositories
- Read file contents from repos
- Create, update, or search issues
- Review pull requests and commits
- Analyze code structure across repositories

**Common tasks:**
- "Show me the recent commits in [repo-name]"
- "Create an issue in [repo-name] for [description]"
- "Search for files containing [keyword] in [repo-name]"
- "List open pull requests in [repo-name]"

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