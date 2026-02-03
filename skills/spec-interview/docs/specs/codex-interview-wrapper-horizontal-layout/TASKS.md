# TASKS

## Phase 0 — Setup / scaffolding
- T0.1 Add new spec folder package
  - Goal: Establish the spec-anchored contract for the horizontal layout + bug fixes.
  - Inputs: Interview decisions (Q0–Q15).
  - Outputs: `SPEC.md`, `PLAN.md`, `TASKS.md`, `ACCEPTANCE.md` in `docs/specs/codex-interview-wrapper-horizontal-layout/`.
  - Steps:
    - Write concise spec with decisions and constraints.
    - Keep Open Questions empty.
  - Done condition: Spec package exists and reflects the interview answers.
  - Depends on: []
  - Risks: Spec diverges from code reality.
  - Test/Verification: N/A (docs only).

## Phase 1 — Core logic
- T1.1 Implement horizontal batch renderer (top/bottom)
  - Goal: Replace left/right split with top status + bottom reader, no truncation.
  - Inputs: Current `_curses_draw_batch` and related UI helpers.
  - Outputs: New rendering function(s) with wrap+scroll in bottom section.
  - Steps:
    - Compute top/bottom heights (~28% / remainder).
    - Render top: progress + scoreboard.
    - Render bottom: wrapped lines for question + options; support vertical scroll.
  - Done condition: Long questions/options render fully via wrap+scroll.
  - Depends on: [T0.1]
  - Risks: Small terminals become unusable.
  - Test/Verification: Manual smoke in terminal; ensure no truncation.

- T1.2 Update interaction model: letter selects, Enter confirms
  - Goal: Make scrolling independent from selection; selection requires Enter.
  - Inputs: Current `_curses_pick_batch` event loop.
  - Outputs: Updated key handling (letters set pending selection, Enter confirms).
  - Steps:
    - Map arrows/PgUp/PgDn/Home/End to scrolling the bottom reader.
    - Map A–J to pending selection state and highlight.
    - On Enter, validate selection (and handle E/H needing text).
  - Done condition: User can scroll freely and select via letter+Enter without conflicts.
  - Depends on: [T1.1]
  - Risks: Harder to discover keys; add concise hint line.
  - Test/Verification: Manual smoke; verify keys behave as specified.

- T1.3 Implement multiline editor for E/H extra text (Ctrl+G confirm)
  - Goal: Allow long free-text without truncation.
  - Inputs: Current `_curses_text_input` (single-line).
  - Outputs: Multiline input mode for E/H.
  - Steps:
    - Use a curses textbox in a multi-line window.
    - Enter inserts newline; Ctrl+G confirms; Esc/q cancels.
  - Done condition: User can enter multi-line text and confirm with Ctrl+G.
  - Depends on: [T1.2]
  - Risks: Terminal differences; document keys in UI hint line.
  - Test/Verification: Manual smoke; paste multi-line text and confirm.

## Phase 2 — Integration
- T2.1 Add batch completeness gating (avoid partial rounds)
  - Goal: Prevent opening UI while Codex is still streaming the round.
  - Inputs: Current `run_interactive()` trigger logic + `parse_batch()`.
  - Outputs: Stronger gating based on final instruction line + minimum question count + settle-time.
  - Steps:
    - Detect “answer instruction” line(s) for the round.
    - Only trigger UI when instruction is present and ≥2 question headers were seen.
    - Keep existing settle-time check.
  - Done condition: Repro “only Q20 shows” no longer happens in common streaming cases.
  - Depends on: [T0.1]
  - Risks: Some renderers omit the line; keep best-effort fallback.
  - Test/Verification: Add unit tests with partial output vs complete output.

- T2.2 Add round-buffering to prevent truncation of long rounds
  - Goal: Ensure Q14–Q20 style rounds aren’t cut by `history_lines`.
  - Inputs: Current `recent` buffer management.
  - Outputs: “round buffer” that captures from first `## Ronda`/`Qn —` through the final instruction.
  - Steps:
    - Track when inside a round and accumulate a dedicated buffer.
    - Prefer parsing from the dedicated buffer when present.
    - Slightly raise default history to reduce risk.
  - Done condition: Long rounds parse as complete batches reliably.
  - Depends on: [T2.1]
  - Risks: Memory growth; cap buffer size defensively.
  - Test/Verification: Unit test with long synthetic rounds.

## Phase 3 — Observability / hardening
- T3.1 Harden input suppression to prevent skipped questions
  - Goal: Avoid stray CR/LF causing unintended extra confirmations/advances.
  - Inputs: Current `_drain_extra_enter_keys` and `suppress_stdin_newline_until`.
  - Outputs: Reliable suppression at all UI boundaries.
  - Steps:
    - Ensure drains happen on all relevant windows (batch view, editor).
    - Keep suppression window short; never drop non-CR/LF data.
  - Done condition: No double-advance observed when answering sequential questions.
  - Depends on: [T1.2, T1.3]
  - Risks: Over-suppression could drop legitimate input; limit to pure CR/LF.
  - Test/Verification: Manual repro attempt; optional small unit test for filter logic.

## Phase 4 — Release / rollout
- T4.1 Update documentation and run existing tests
  - Goal: Ensure changes are discoverable and regressions are caught.
  - Inputs: Existing `scripts/tests/test_codex_interview_wrapper.py`.
  - Outputs: Updated tests and a short doc note if needed.
  - Steps:
    - Add tests for new gating logic.
    - Run `python -m unittest` from `scripts/tests`.
  - Done condition: Tests pass; manual smoke test checklist completed.
  - Depends on: [T2.2, T3.1]
  - Risks: Terminal-only behaviors hard to unit test; rely on manual smoke.
  - Test/Verification: Unit tests + manual.

## Chunking guidance

- Suggested implementation chunk size: 1–2 tasks per chunk
- Review cadence: after each chunk, verify the acceptance criteria impacted by those tasks
- Stop points: safe to stop after each phase (Phase 1, Phase 2, Phase 3)

## Execution status
- Status: NOT_STARTED
- Current task: T0.1
- Completed tasks: (optional)
- Last updated: 2026-01-30

