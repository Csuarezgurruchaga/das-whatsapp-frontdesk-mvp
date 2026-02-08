# ACCEPTANCE — codex-interview-wrapper-horizontal-layout

## A1 — Horizontal layout structure

- The batch UI renders in two sections:
  - Top section (~25–30% height): progress + compact state.
  - Bottom section (~70–75% height): current question + all options.

## A2 — No truncation in reader

- In the bottom section, question text and all option labels render with wrap and can be fully read via vertical scrolling.
- No option label is truncated with `...` in the bottom section.

## A3 — Navigation and selection keys

- Scrolling works with ↑/↓, PgUp/PgDn, Home/End.
- Pressing a letter A–J selects that option as “pending” (visible in UI).
- Enter confirms the pending selection and advances to the next question.

## A4 — Multiline extra text (E/H)

- Choosing `E` (Other) or `H` (Compare with custom text) allows entering multiline text.
- Enter inserts newline; Ctrl+G confirms submission.

## A5 — Batch completeness: no partial UI

- The wrapper does not open the batch UI while Codex is still streaming the round.
- A round like “Ronda 3 (Q14–Q20)” does not result in a UI that only shows `Q20` unless Codex truly output only that content.

## A6 — No skipped questions

- Answering sequential questions in a batch does not skip intermediate questions due to stray/extra Enter events.

## A7 — Semantics preserved

- The wrapper still submits answers as a single comma-separated line with `Qn=...` pairs (e.g., `Q14=C, Q15=A, Q16=E: ...`) and includes the Enter/CR so Codex processes it without additional user action.

