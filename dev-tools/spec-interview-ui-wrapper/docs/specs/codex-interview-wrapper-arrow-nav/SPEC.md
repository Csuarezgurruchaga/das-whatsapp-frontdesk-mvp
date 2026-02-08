# codex-interview-wrapper-arrow-nav

## Summary

Update the curses batch UI in `codex-interview-wrapper.py` so users can navigate answer options with arrow keys:

- **↑/↓ moves the pending option selection** (instead of scrolling the reader).
- Each question **starts with A preselected** (or the first available option).
- Navigation **wraps**: pressing ↑ on the first option selects the last; pressing ↓ on the last selects the first.

Keep the interview semantics intact (same `Qn=...` output format and same Codex interaction). This spec is additive to the existing horizontal layout work.

## Goals / Non-goals

### Goals

- Arrow key navigation:
  - **↑/↓**: move pending selection between available options (A–J) for the current question.
  - **Wrap-around** at the ends.
- Default selection:
  - When a question becomes active, set pending selection to **A** (if present), otherwise the **first available option**.
- Preserve confirmation model:
  - **Enter confirms** the pending selection and advances.
  - Typing **A–J** continues to set the pending selection directly (shortcut).
- Preserve readability for long text:
  - Reader scrolling remains available via **PgUp/PgDn** and **Home/End**.

### Non-goals

- Changing the `spec-interview` skill content, ordering, numbering, or semantics.
- Changing the wrapper’s output format. Must remain:
  - `Qn=A`
  - `Qn=E: texto`
  - `Qn=H: A vs C`
- Adding non-stdlib dependencies.
- Adding backtracking/editing of previous answers.

## Constraints

- Keys:
  - **Option navigation:** ↑/↓ (wrap-around).
  - **Reader scroll:** PgUp/PgDn/Home/End.
  - **Confirm:** Enter.
  - **Cancel:** q or Esc.
  - **E/H multiline editor:** Enter inserts newline, Ctrl+G confirms.
- No truncation of reader text (wrap + scroll remains).

## Open Questions

None.

## Changelog

- 2026-01-30 — Add arrow-key option navigation + default A preselect + wrap-around

