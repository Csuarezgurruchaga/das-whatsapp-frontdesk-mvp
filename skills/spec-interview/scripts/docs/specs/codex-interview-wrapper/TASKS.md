# Tasks

- [ ] Make `codex-interview-wrapper.py` PTY-based and dependency-free.
- [ ] Support parsing multi-question rounds (`Q0…Qn`) with inline meta options.
- [ ] Implement a batch-view `curses` UI that shows the whole round and advances sequentially (no backtracking).
- [ ] Add a dedicated options panel for the current question (up/down to choose, Enter confirms).
- [ ] Implement inline `E) Other` text entry.
- [ ] Ensure meta options send partial answers + meta and continue the wizard.
- [ ] Add compare (H) sub-selector with pre-generated A–D pairs + free-text option.
- [ ] Ensure `H) Compare` + custom text returns to the batch flow (no accidental auto-submit / exit).
- [ ] Allow Qn-only detection and manual answer entry when options are missing.
- [ ] Add compact option display with a toggle for full text.
- [ ] Ensure answers are submitted to Codex (line + newline) without requiring manual Enter.
- [ ] Detect "resend round answers" prompts after meta responses and re-open the UI (avoid false positives / duplicate batches).
- [ ] Convert `interview_ui.sh` to a runnable script.
- [ ] Add `unittest` coverage for `parse_batch` and formatting.
- [ ] Verify acceptance steps manually inside the container.

## Execution status

- Status: TODO
- Current task: Make `codex-interview-wrapper.py` PTY-based and dependency-free.
- Last updated: 2026-01-28
