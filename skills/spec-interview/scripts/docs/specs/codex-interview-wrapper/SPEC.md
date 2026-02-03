# codex-interview-wrapper

## Goal

Provide a small Python wrapper that improves the UX of answering the `spec-interview` skill prompts in Codex CLI by:

- Detecting a `spec-interview` “round” printed by Codex (multiple questions `Q0…Q9` with options `A)…J)`).
- Presenting a local TUI selector (arrow keys) to choose answers.
- Sending a **single-line** answer back to Codex (e.g. `Q0=A, Q1=C, Q2=E: ...`).

Primary target environment: running **inside the Docker container** started by `sb codex`.

## Spec contract

> The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog.

## Non-goals

- Re-implementing `spec-interview` logic itself.
- Adding non-stdlib Python dependencies (no `pexpect`, no `gum`).
- Attaching to an already-running Codex process (the wrapper spawns Codex).
- Supporting arbitrary navigation and editing within a batch (answers are collected sequentially; no backtracking).

## User experience

## Decisions

These decisions come from the wrapper's own `spec-interview` round (not the Codex session being wrapped):

- Layout: single scrollable screen that shows the whole batch, with a "current question" focus. (Q0=A)
- Options UX: for the current question, always show an options list/panel where the user moves through options and confirms with Enter. (Q1=C)
- Editing: once a question is answered, the user cannot go back and change it. (Q2=C)
- E) Other: inline text entry (no modal) for free text. (Q3=C)
- H) Compare: secondary screen with pre-generated pairs (when possible) + "Other (write)". (Q4=A)
- Submit: automatically send the answer line immediately after the last question is answered (no final confirmation screen). (Q5=A)
- Submit mechanism: wrapper must send the newline/Enter to Codex so the line is processed without the user pressing Enter manually. (Q6=A)

### Happy path (full round)

1. User runs the wrapper, which spawns `codex --no-alt-screen`.
2. User invokes the `spec-interview` skill inside Codex.
3. When Codex prints a round of questions (`Q0 — ...` … `Q9 — ...`), the wrapper:
   - Shows a single batch screen listing all questions.
   - Focuses the current question (starting from the first in the round).
   - Shows an options list/panel for the current question.
   - Collects one choice per question, then auto-advances focus to the next question.
   - Sends one line with comma-separated pairs in order:
     - Example: `Q0=A, Q1=B, Q2=E: texto`
   - Sends immediately after the last selection and includes the Enter/newline so Codex processes it (no extra Enter required).

### Meta options

If the user selects a meta option (`G`, `H`, `I`, `J`) for a question:

- The wrapper records the meta choice and **continues** collecting answers for the rest of the round.
- After the last question of the round, the wrapper sends a single line including all pairs (including any meta pairs).
- Codex may respond with explanations and re-ask some questions; the wrapper should be able to trigger again on the follow-up prompts.

Examples:
- `Q0=G`
- `Q0=A, Q1=I`
- `Q0=A, Q1=H: A vs C`

### Compare (H) selection UI

When the user selects `H) Compare` for a question:

- The wrapper opens a secondary selector with pre-generated pairs for simple choices.
  - If the question has options `A–D`, generate all unique pairs:
    - `A vs B`, `A vs C`, `A vs D`, `B vs C`, `B vs D`, `C vs D`
- Always include one extra option to allow free text (e.g. “Other (write)”).
- If no viable pair list can be generated, fall back to free-text entry.

The selected pair is sent as `Qn=H: A vs C`.

### Other (E) text entry UI

When the user selects `E) Other` for a question:

- The UI switches the current question panel into an inline text entry mode (single-line).
- Enter confirms the text and returns to the batch flow, auto-advancing to the next question.

### Cancellation / fallback

- If `curses` UI cannot be used (no TTY or error), fall back to a prompt that asks for the letter.
- User can cancel selection with `q`/Esc; wrapper returns to normal Codex passthrough.

## Detection & parsing requirements

- Must parse question headers: `Q<number> — <title>` (accept both em dash `—` and `-`).
- Question headers may be prefixed by a UI marker like `›` or `•`; these should be accepted.
- Must parse options in two formats:
  - One-per-line: `A) ...`
  - Multiple options in a single line separated by commas:
    - `G) Explain..., H) Compare..., I) Recommend, J) Show examples`
- A batch should trigger even if a question header exists without any `A)`/`B)` options
  (aggressive mode). If a question has no options, prompt the user for a manual answer.

## Option list display

- Default to a compact option list (single-line truncation).
- Provide a toggle to show full option text when needed.

## Defaults / CLI

- Default spawn command: `codex --no-alt-screen`
- Default shell: `bash`

## Open Questions

None.

## Acceptance criteria

See `docs/specs/codex-interview-wrapper/ACCEPTANCE.md`.
