# sb-interview-ui shortcut

To avoid `cd ~/.codex/dev-tools/spec-interview-ui-wrapper/scripts` and manually run the Python script,
a lightweight shortcut script is provided (`sb-interview-ui`). It simply executes
`codex-interview-wrapper.py` via `python3` so you can call the UI from anywhere.

## Install the shortcut (run once)

1. Make sure a directory such as `~/bin` or `~/.local/bin` is on your `PATH`.
2. Create a symlink pointing at the new script, for example:

   ```bash
   ln -sf "$HOME/.codex/dev-tools/spec-interview-ui-wrapper/scripts/sb-interview-ui" "$HOME/.local/bin/sb-interview-ui"
   ```

3. Ensure the directory is earlier in your `PATH` than the default `sb` commands so the shortcut
   can be invoked directly:

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

4. Now you can start the UI with:

   ```bash
   sb-interview-ui --cmd "codex --no-alt-screen"
   ```

   or supply any other `codex-interview-wrapper.py` arguments you need.

If you’d rather match your existing `sb` naming, just create a second symlink such as
`$HOME/.local/bin/sb-interview` that points to the same script.

## UI keys (curses mode)

- Navigate options: ↑/↓ (wrap-around)
- Scroll reader: PgUp/PgDn, Home/End
- Select: A–J (sets pending selection directly)
- Confirm: Enter (records selection and advances)
- Cancel: q or Esc
- Multiline text for `E)` / `H)`: Enter inserts newline, Ctrl+G confirms
