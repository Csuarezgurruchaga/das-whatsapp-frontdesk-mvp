# Promotion workflow

## Trigger conditions (mandatory)
Run promotion only when:
- the user explicitly asks to promote/merge, OR
- `Status: DONE` in `TASKS.md` AND `impl/<slug>` is ahead of `dev`
  - "ahead" means: there are commits on `impl/<slug>` that are not present in `dev`.

Do NOT promote automatically in any other case.

## Promote to dev (staging)
Prefer PR over direct merge.

### Preflight (before creating PR)
- Confirm source branch is `impl/<slug>` and target branch is `dev`.
- Ensure the PR body includes:
  - tasks completed
  - TASKS progress done/total
  - verification summary
  - acceptance status

### Create PR
- Source: `impl/<slug>`
- Target: `dev`
- Title: `(<slug>) Promote implementation to dev`
- Body MUST include:
  - Tasks completed
  - TASKS progress done/total
  - Verification summary
  - Acceptance status

### Merge behavior
- If the user asked for auto-merge AND checks are green:
  - Merge PR using a non-destructive merge strategy (merge commit or squash).
  - No force-push. No rebase of shared branches.
  - Confirm `dev` now contains the deliverables.
- If the user did NOT request auto-merge:
  - STOP after creating the PR and report PR link/details.

## Promote to main (production) — only if user asks
This skill MUST NOT promote to `main` unless the user requests it.

If requested:
- Ensure `dev` is validated (tests/build/smoke as required by ACCEPTANCE).
- Create PR `dev` → `main`
- Title: `(<slug>) Release to main`
- Body includes acceptance verification + deployment notes
