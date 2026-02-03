---
name: pr-simplifier
description: Simplify and clean up code changes (PR-ready) without changing behavior.
metadata:
  short-description: Simplify diffs, preserve behavior
---

# Purpose

Take the current working tree changes (or a provided diff / file list) and refactor/simplify them to be easier to review and maintain, while preserving **exact behavior**.

This skill is intended to be run:
- At the end of a long coding session
- Before opening or cleaning up a Pull Request
- When a diff is correct but unnecessarily complex

# Hard constraints (MUST NOT violate)

- **Do NOT change external behavior**
- **Do NOT change public APIs** unless explicitly instructed
- **Do NOT remove features**
- **Do NOT add new features**
- Outputs must be identical or functionally equivalent
- Respect existing project conventions (style, patterns, lint rules)
- Keep diffs as small and reviewable as possible

If a simplification risks changing behavior, **do not apply it**.

# What “simplify” means (priority order)

1. Reduce cognitive load (deep nesting, clever tricks, dense expressions)
2. Improve naming (variables, functions, helpers)
3. Remove duplication when it clearly improves clarity
4. Extract helpers only if it reduces repetition or complexity
5. Normalize error handling to existing project patterns
6. Preserve formatting unless it improves clarity or fixes inconsistency
7. Avoid large refactors unless strictly necessary

Clarity > cleverness. Explicit > implicit.

# Scope detection

1. If the user provides:
   - A file list → use it
   - A diff → use it
2. Otherwise:
   - Inspect `git status`
   - Use `git diff` to identify modified files

Ignore unrelated or untouched files.

# Workflow

1. Identify modified files and relevant diffs
2. For each file:
   - Identify confusing or overly complex sections
   - Apply minimal refactors that preserve behavior
   - Keep changes localized to touched code
3. Verify correctness:
   - Run existing tests or linters if available
   - If tests are too slow, run targeted checks
4. Finalize:
   - Ensure diffs are clean and intentional
   - Avoid cosmetic-only churn

# Output requirements

After applying changes:

- Modify files directly in the working tree
- Then provide:
  - A short summary (max 8 bullets)
  - Commands executed (tests / linters)
  - Any risky areas and how to validate them
  - Optional follow-up suggestions (clearly marked)

Do NOT include unnecessary explanations.
Focus on producing a clean, review-ready diff.

