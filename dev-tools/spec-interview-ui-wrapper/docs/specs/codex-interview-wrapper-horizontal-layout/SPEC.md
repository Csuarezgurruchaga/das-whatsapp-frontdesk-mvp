# codex-interview-wrapper-horizontal-layout

## Summary

Refactor the TUI layout in `scripts/codex-interview-wrapper.py` to improve readability for long `spec-interview` rounds by switching from a vertical split (left/right) to a horizontal split (top status + bottom reader). Keep the interview semantics intact (same Qn=A format and same Codex interaction), while also fixing two UX-critical bugs observed in real use:

- **Partial batch render:** UI sometimes triggers while Codex is still streaming the round, resulting in only the last question (e.g., `Q20`) being shown.
- **Skipped question:** after answering a question, the UI sometimes advances too far (e.g., `Q28` → `Q30`), consistent with “stray Enter” / input leakage.

Primary target: running inside the Docker container started by `sb codex`.

## Goals / Non-goals

### Goals

- Replace the current batch view with a **horizontal layout**:
  - **Top section (~25–30% height):** batch progress + compact interview state.
  - **Bottom section (~70–75% height):** full question + all options, wrapped, scrollable, no truncation.
- Bottom section supports:
  - automatic word-wrap (multi-line)
  - vertical scroll (no truncation)
  - answer selection by single letter (A–J), confirmed with Enter
- Fix the two UX bugs:
  - do not open the batch UI until the round is complete/stable
  - prevent “extra Enter” from being interpreted as an additional confirmation/advance

### Non-goals

- Changing the `spec-interview` skill’s content, semantics, ordering, numbering, or answer format.
- Changing the wrapper’s output format: must remain `Qn=A, Qm=E: ...`.
- Adding non-stdlib dependencies.
- Adding backtracking/editing of previous answers (remains “no backtracking”).

## Constraints

- **Semantics unchanged:** the wrapper must continue to send a single comma-separated answer line with `Qn=...` pairs, in batch question order.
- **Key input model:**
  - **Scroll:** Arrow keys + PgUp/PgDn + Home/End.
  - **Selection:** A–J sets “pending selection”; **Enter confirms** and advances to next question.
- **Text rendering:** no truncation of question/option text in the bottom section; always wrap and allow scroll.
- **Compatibility:** curses-based UI remains the default when TTY is available; prompt-based fallback remains.

## Key Flows

1) **Detect round**
   - Wrapper watches Codex output and detects a `spec-interview` round/batch.
   - Must not trigger mid-stream (see “Batch completeness gating”).

2) **Render batch UI (horizontal)**
   - Top section shows progress + state summary.
   - Bottom section renders current question fully (title + all options) with wrap + vertical scroll.

3) **Answer a question**
   - User scrolls to read (optional).
   - User presses a letter A–J to select; UI indicates the pending selection.
   - User presses Enter to confirm; wrapper records `Answer(letter, extra?)` and advances to next question.

4) **E) Other / H) Compare / meta**
   - `E` and `H` require extra text.
   - Extra text entry uses a **multiline editor** (curses) with:
     - Enter inserts newline
     - **Ctrl+G confirms** (Textbox convention)
   - Meta options (`G/I/J` and `H` when used as meta help) keep existing wrapper semantics:
     - triggering a meta request can open the existing help+answer flow, but the final recorded answer must still be `Qn=<letter>` or `Qn=H: ...` per current wrapper behavior.

5) **Submit**
   - After the last question in the batch is answered, wrapper sends the formatted line to Codex and includes Enter (CR).

## Data / Interfaces

- **Input (from Codex):** streamed terminal output, parsed into:
  - `Batch(questions=[Question(qid, title, options)], signature=...)`
- **User input (to wrapper UI):** key events from curses.
- **Output (to Codex):** one line in the format:
  - `Q14=C, Q15=A, Q16=B, ...`
  - `Q14=E: <texto>`
  - `Q14=H: A vs C`

## Edge cases & Failure modes

- **Small terminals:** If height/width is too small to render both sections sensibly, degrade gracefully:
  - keep top minimal (1–2 lines) and allocate remaining space to bottom reader.
- **Very long option labels:** bottom section must still show fully via wrap+scroll.
- **Batch appears truncated in buffer:** if the parser sees only a subset of questions, the UI must not open; it should wait for completeness gating or fall back.
- **Input leakage / extra Enter:** ensure that after leaving curses input modes, pending CR/LF does not advance the batch.

## Observability

- Keep existing `--debug` logging approach.
- Add/keep logs (debug only) for:
  - batch detection (qids + signature)
  - completeness gating decisions (why UI did/didn’t open)
  - input suppression events (dropping pure CR/LF after UI close)

## Security / Privacy

- No new external I/O or persistence beyond current behavior.
- Wrapper must not log user free-text answers unless `--debug` is enabled (status quo expectation).

## Open Questions

None.

## Decision Log

- **Decision:** Implement horizontal layout (top status + bottom reader) with no truncation.
  - **Rationale:** long text is currently unreadable due to narrow columns; wrap+scroll is the priority.
  - **Risks / mitigations:** small terminals → degrade top section and keep bottom scrollable.

- **Decision:** Scope includes both fixes (partial batch + skipped question) in addition to layout refactor.
  - **Rationale:** both bugs directly harm interview correctness/UX; layout-only change would not address them.
  - **Risks / mitigations:** keep changes tightly scoped to trigger gating and input draining/suppression.

- **Decision:** Navigation is “scroll with arrows”, “select with letter”, “Enter confirms”.
  - **Rationale:** avoids conflicts between scrolling and selection; keeps muscle-memory for long reading.

- **Decision:** Batch progress in two lines (batch progress + global best-effort if available).
  - **Rationale:** gives immediate orientation without needing a side panel.

- **Decision:** Do not show the final instruction (“Responde en UNA sola línea…”) in the bottom reader.
  - **Rationale:** reduce noise; the wrapper always enforces/produces the correct answer format.

- **Decision:** Batch completeness gating: wait for the presence of the final “Responde en UNA sola línea…” line and at least two `Qn —` headers before opening UI.
  - **Rationale:** prevents triggering while Codex is still printing; addresses “only Q20” symptom.
  - **Risks / mitigations:** for rounds that don’t include that line, fall back to existing settle-time heuristics or prompt mode (best-effort).

- **Decision:** Buffer strategy to avoid losing early questions: implement a round-buffer approach and also raise the default history somewhat.
  - **Rationale:** protects against long rounds and status-line repaint noise.

- **Decision:** Multiline extra text input uses Ctrl+G to confirm; Enter inserts newline.
  - **Rationale:** supports long free-text without truncation; matches `curses.textpad` convention.

## Changelog

- 2026-01-30 — Initial spec for horizontal layout + UX bug fixes
  - reason: improve legibility and prevent incorrect batch handling
  - impact: update curses rendering, batch trigger gating, and input suppression

## Glossary

- **Batch/Round:** A `spec-interview` “Ronda N (Qx–Qy)” block printed by Codex containing multiple `Qn — ...` questions.
- **Completeness gating:** Heuristics that ensure the wrapper opens the batch UI only once the round output is complete and stable.

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

