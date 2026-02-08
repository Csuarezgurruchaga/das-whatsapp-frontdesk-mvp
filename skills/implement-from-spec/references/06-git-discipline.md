# Git discipline

Goal: keep work auditable, resumable, and safe. Git history must mirror TASK execution.

## STOP protocol (mandatory)
If any Git safety condition is not met:
- STOP before editing code.
- Do NOT stage/commit/push anything.
- Report the exact state and the minimal steps required to correct it.

If you already made changes before detecting the issue:
- Report it.
- Revert changes (or instruct the user how) before proceeding.
- Do NOT continue implementation in the same run.

## Branch rules (hard)
All implementation MUST happen on:
- `impl/<slug>`

Never implement directly on:
- `main` (or any protected branch)
- `dev` (integration branch)

### Hard stop: wrong branch
If you are on `main`, `dev`, or any branch other than `impl/<slug>`:
- STOP and switch/create `impl/<slug>` before any edits.

### Hard stop: detached HEAD / no branch
If `git status` shows "Not currently on any branch":
- STOP and attach to `impl/<slug>`. Do not implement while detached.

### Hard stop: dirty state before switching
If you have unstaged/staged changes and still need to switch branches:
- STOP and either commit them to the correct branch (only if valid and task-scoped),
  or revert/stash them (prefer revert if accidental).
- Do not carry accidental changes across branches.

## Base branch rule
Determine base for `impl/<slug>`:
- If `dev` exists: base is `dev`
- Else: base is `main`

Rule:
- `impl/<slug>` MUST be created/synced from the correct base before implementing.

## Commit rules (hard)
- Prefer: 1 task = 1 commit
- Never mix multiple TaskIDs in the same commit.

Commit message format:
- `<type>(<slug>): <TaskID> <short title>`

Allowed types:
- `feat`, `fix`, `chore`, `refactor`, `docs`, `test`

## Staging rules (hard)
- Stage only files relevant to the current task.
- If unrelated diffs are present, revert them before committing.

## Push rules (hard)
Push after each chunk (after 1–2 tasks).

- First push:
  - `git push -u origin impl/<slug>`
- Subsequent pushes:
  - `git push`

If push fails:
- STOP and report the exact error output.

## PR / merge safety rules
- Prefer PR for promotion to `dev`.
- No force-push.
- No rebasing shared branches.

Promotion logic is defined in:
- `references/09-promotion-workflow.md`
