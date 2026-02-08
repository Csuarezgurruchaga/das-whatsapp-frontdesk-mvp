# Plan

## Implementation steps

1. Refactor `codex-interview-wrapper.py` to:
   - Spawn Codex in a PTY (`pty.fork`) using `bash -lc`.
   - Stream child output to stdout (so Codex is visible).
   - Keep a sliding window of recent lines for parsing.
   - Detect a `spec-interview` batch (multiple questions per round).
   - Drive a batch-view TUI (curses) that shows the full round and advances question-by-question.
   - For the focused question, show an options panel and confirm via Enter (no editing/backtracking).
   - Implement inline text entry for `E) Other`.
   - Add compare (H) secondary selector with pre-generated pairs + free-text option.
   - Send a single-line response back to the child process and include the Enter/newline so Codex processes it (no manual submit).
   - Harden key handling so Enter/Delete behave consistently across terminals/PTYs.
   - Detect "resend the round answers" prompts after meta responses and re-open the batch UI.
   - Allow Qn-only batches (no A/B) with manual answer prompt.
   - Provide compact list with toggle for full option text.
2. Convert `interview_ui.sh` into an executable script (remove installer wrapper).
3. Add unit tests for parsing and formatting with `unittest`.
4. Document acceptance checks and basic usage.
