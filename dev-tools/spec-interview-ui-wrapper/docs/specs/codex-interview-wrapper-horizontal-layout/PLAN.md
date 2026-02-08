# PLAN — codex-interview-wrapper-horizontal-layout

## Overview

Implement a horizontal curses layout optimized for reading long `spec-interview` questions, while keeping the existing wrapper semantics and answer formatting. In the same change set, harden batch detection (avoid partial/streaming rounds) and input handling (avoid “extra Enter” skipping questions).

## Phases

### Phase 0 — Confirm baseline behavior

- Identify current batch detection trigger points and current curses rendering entrypoints.
- Document current known failure modes (partial batch, skipped question) in terms of repro steps and likely causes.

### Phase 1 — Horizontal layout refactor (presentation-only)

- Replace the existing left/right split rendering in the batch UI with:
  - Top: batch/global progress + compact scoreboard.
  - Bottom: scrollable reader rendering the full current question (title + all options) with wrap.
- Ensure no truncation is used for the bottom reader (wrap + scroll instead).

### Phase 2 — Interaction model updates (still semantics-preserving)

- Implement selection by letter A–J (sets pending selection).
- Confirm with Enter to record and advance.
- Keep scroll controls (arrows/PgUp/PgDn/Home/End) dedicated to reading.
- Update E/H input to multiline editor with Ctrl+G confirm.

### Phase 3 — Batch completeness gating and buffering

- Add “round complete” detection to delay opening the UI until the round’s final instruction line appears (best-effort), plus a minimum-question threshold and settle-time stability.
- Add a round-buffer strategy so long rounds aren’t truncated by a fixed `history_lines` size.
- Keep behavior robust when Codex re-asks after meta help (avoid false triggers from prose).

### Phase 4 — Fix input leakage / skip bug

- Strengthen post-UI input suppression so pure CR/LF sequences are dropped for a short window, without dropping real typed input.
- Ensure drain/flush happens at all transitions (entering/leaving curses UI, leaving multiline editor).

### Phase 5 — Verification

- Update/add unit tests for batch detection heuristics as needed (stdlib `unittest`).
- Manual smoke tests in a real terminal:
  - long round renders fully with wrap+scroll
  - no skipped questions on Enter
  - no partial batch UI when Codex is still streaming

## Rollout / rollback

- Rollout as a minimal diff gated behind existing flags (keep `--no-curses` fallback).
- Keep changes localized so reverting is straightforward (layout/render functions + trigger heuristics).

