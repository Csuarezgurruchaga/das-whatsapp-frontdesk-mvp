#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import codecs
import curses
import curses.ascii
import curses.textpad
import fcntl
import hashlib
import os
import pty
import re
import selectors
import shutil
import shlex
import signal
import struct
import subprocess
import sys
import termios
import textwrap
import time
import tty
from contextlib import contextmanager
from dataclasses import dataclass


# Broad ANSI/VT100 control sequence matchers:
# - CSI: ESC[ ... @-~ (covers private modes like ESC[?25h and bracketed paste ESC[?2004h)
# - SS3: ESC O <final> (common for function keys / some arrow-key terminals)
# Based on xterm control sequence grammar.
ANSI_CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ANSI_SS3_RE = re.compile(r"\x1bO.")
# Question headers/options sometimes get prefixed by UI markers (e.g. "›", "•", "│") depending on the Codex renderer.
# Allow an optional leading marker token before "Qn" / before "A) ..." lines.
_UI_PREFIX = r"(?:[›•│]\s*)?"
Q_LINE_RE = re.compile(rf"^\s*{_UI_PREFIX}(Q\d+)\s*(?:—|-|\))\s*(.+?)\s*$")
OPT_LINE_RE = re.compile(rf"^\s*{_UI_PREFIX}([A-J])\)\s*(.+?)\s*$")
OPT_INLINE_RE = re.compile(r"\b([A-J])\)\s*([^/,]+?)(?=(?:\s*[/,]\s*[A-J]\))|$)")
OPT_BULLET_RE = re.compile(rf"^\s*[-*]\s*{_UI_PREFIX}([A-J])\s*[\)\(]\s*(.+?)\s*$")
Q_REF_RE = re.compile(r"\b(Q\d+)\s*=")

META_FALLBACK_LABELS: dict[str, str] = {
    "G": "Explain options",
    "H": "Compare options",
    "I": "Recommend",
    "J": "Show examples",
}

CODEX_CHROME_RE = re.compile(
    r"(?:\bcontext left\b|\bfor shortcuts\b|\bWorking\(|\bCode mode\b)", re.IGNORECASE
)
RESEND_PROMPT_RE = re.compile(
    # The spec-interview skill sometimes asks to re-send the round answers after a
    # meta/help response, but wording varies across renderers and languages.
    r"(?:"
    r"\bplease\s+resend\b.*\bround\s+answers\b"
    r"|\bformat\s+reminder:\s*Q\d+\s*="
    r"|\breply\s+in\s+one\s+line\b.*\bQ\d+\s*="
    r"|\bwe\s+still\s+need\s+the\s+actual\s+answer\s+letters\b"
    r"|\bresponde\s+en\s+una\s+sola\s+linea\b.*\bQ\d+\s*="
    r")",
    re.IGNORECASE,
)

ROUND_HEADER_RE = re.compile(r"^\s*(?:##\s*)?(?:Ronda|Round)\b", re.IGNORECASE)
ANSWER_INSTRUCTION_RE = re.compile(
    r"(?:"
    r"responde\s+en\s+una\s+sola\s+l[ií]nea"
    r"|reply\s+in\s+one\s+line"
    r"|answer\s+in\s+one\s+line"
    r")",
    re.IGNORECASE,
)


def _count_q_headers(lines: list[str], *, max_lookback: int = 2000) -> int:
    window = lines[-max_lookback:] if len(lines) > max_lookback else lines
    return sum(1 for ln in window if Q_LINE_RE.match(ln))


def _has_answer_instruction(lines: list[str], *, max_lookback: int = 2000) -> bool:
    window = lines[-max_lookback:] if len(lines) > max_lookback else lines
    return any(ANSWER_INSTRUCTION_RE.search(ln) for ln in window)


def _batch_completeness_gate(
    lines: list[str],
    *,
    quiet_for: float,
    settle_sec: float,
    min_q_headers: int = 2,
    no_instruction_extra_quiet_mult: float = 4.0,
) -> tuple[bool, str]:
    """
    Best-effort gating to avoid opening the batch UI mid-stream or with a truncated
    buffer (e.g. only the last question).

    Rules:
    - Always require output to be quiet for settle_sec.
    - Require at least min_q_headers "Qn —" headers in the buffered text.
    - Prefer requiring the "answer in one line" instruction, but allow a fallback
      if that instruction line is missing after a longer quiet window.
    """
    if quiet_for < settle_sec:
        return False, "not settled"

    q_headers = _count_q_headers(lines)
    if q_headers < min_q_headers:
        return False, f"need >= {min_q_headers} headers (saw {q_headers})"

    if _has_answer_instruction(lines):
        return True, "has instruction + headers"

    extra_quiet = max(settle_sec, settle_sec * no_instruction_extra_quiet_mult)
    if quiet_for >= extra_quiet:
        return True, "fallback (headers + extra quiet)"

    return False, "missing instruction (waiting)"


class RoundBuffer:
    """
    Captures the full text of a spec-interview round so we don't lose early questions
    when the global history buffer is truncated.
    """

    def __init__(self, *, max_lines: int = 8000):
        self.max_lines = max_lines
        self.reset()

    def reset(self) -> None:
        self.active = False
        self._lines: list[str] = []
        self._q_headers = 0
        self._saw_instruction = False
        self.complete_lines: list[str] | None = None
        self._overflowed = False

    @property
    def lines(self) -> list[str]:
        return self._lines

    def preferred_lines(self, recent: list[str]) -> list[str]:
        if self.complete_lines is not None:
            return self.complete_lines
        if self.active and self._lines:
            return self._lines
        return recent

    def _start_new(self, first_line: str) -> None:
        self.active = True
        self._lines = [first_line]
        self._q_headers = 1 if Q_LINE_RE.match(first_line) else 0
        self._saw_instruction = bool(ANSWER_INSTRUCTION_RE.search(first_line))
        self.complete_lines = None
        self._overflowed = False

    def push_line(self, line: str) -> None:
        if not line.strip():
            return

        is_round_start = bool(ROUND_HEADER_RE.search(line))
        is_q_header = bool(Q_LINE_RE.match(line))

        if (not self.active and self.complete_lines is None) and (is_round_start or is_q_header):
            self._start_new(line)
            return

        if self.complete_lines is not None and (is_round_start or is_q_header):
            # Start a new round once we see the next round/question header.
            self._start_new(line)
            return

        if not self.active:
            return

        if is_round_start and self._lines:
            # Defensive: some renderers might print multiple round headers; treat it as a reset.
            self._start_new(line)
            return

        if len(self._lines) >= self.max_lines:
            self._overflowed = True
            return

        self._lines.append(line)
        if is_q_header:
            self._q_headers += 1
        if ANSWER_INSTRUCTION_RE.search(line):
            self._saw_instruction = True

        # Mark completion when we have enough question headers and we see the instruction line.
        if self._saw_instruction and self._q_headers >= 2:
            self.complete_lines = list(self._lines)
            self.active = False


def strip_ansi(s: str) -> str:
    # Order matters: strip CSI + SS3 sequences, then any stray ESC chars.
    s = ANSI_CSI_RE.sub("", s)
    s = ANSI_SS3_RE.sub("", s)
    return s.replace("\x1b", "")


@dataclass(frozen=True)
class Option:
    letter: str
    label: str


@dataclass(frozen=True)
class Question:
    qid: str
    title: str
    options: list[Option]


@dataclass(frozen=True)
class Answer:
    letter: str
    extra: str | None = None


@dataclass(frozen=True)
class Batch:
    questions: list[Question]
    signature: str


class UserCanceled(Exception):
    pass


_ENTER_KEYS = {10, 13, curses.KEY_ENTER, curses.ascii.NL}
_META_LETTERS = {"G", "H", "I", "J"}
_REOPEN_UI_KEY = 15  # Ctrl+O
_DETAIL_CLOSE_KEYS = {27, ord("q"), ord("d"), ord("D"), *_ENTER_KEYS}


def _drain_extra_enter_keys(win) -> None:
    """
    Some terminals deliver Enter as multiple key events (e.g. CRLF). If we don't
    drain the extra event(s), the next screen can immediately "auto-Enter".
    Only drains Enter-ish keys and pushes back the first non-Enter key.
    """
    win.nodelay(True)
    try:
        # Small "settle" window if we observe an Enter key: some terminals send CR and LF
        # slightly separated in time, so a simple immediate drain can miss the tail.
        did_probe = False
        saw_enter = False
        settle_deadline = 0.0
        for _ in range(64):
            ch = win.getch()
            if ch == -1:
                if not did_probe:
                    # One tiny probe to catch a delayed LF that arrives just after the
                    # caller consumed the first Enter key event.
                    did_probe = True
                    time.sleep(0.01)
                    continue
                if saw_enter:
                    now = time.time()
                    if settle_deadline == 0.0:
                        settle_deadline = now + 0.06
                    if now < settle_deadline:
                        time.sleep(min(0.01, settle_deadline - now))
                        continue
                break
            if ch in _ENTER_KEYS:
                saw_enter = True
                continue
            curses.ungetch(ch)
            break
    finally:
        win.nodelay(False)


def _consume_reopen_shortcut(data: bytes, *, can_reopen: bool) -> tuple[bool, bytes]:
    """
    Detect and remove the "reopen batch UI" shortcut from raw stdin bytes.

    Returns:
      (reopen_requested, remaining_bytes_to_forward)
    """
    if not can_reopen or not data:
        return False, data

    reopen_requested = False
    out = bytearray()
    for b in data:
        if b == _REOPEN_UI_KEY:
            reopen_requested = True
            continue
        out.append(b)
    return reopen_requested, bytes(out)


def _dedupe_options(options: list[Option]) -> list[Option]:
    seen: set[str] = set()
    out: list[Option] = []
    for opt in options:
        if opt.letter not in seen:
            out.append(opt)
            seen.add(opt.letter)
    return out


def _compact_label(label: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    single = label.replace("\n", " ").strip()
    if len(single) <= max_chars:
        return single
    if max_chars <= 3:
        return single[:max_chars]
    return single[: max_chars - 3].rstrip() + "..."


def _is_option_continuation_line(line: str) -> bool:
    """Best-effort heuristic for wrapped option-label continuations."""
    stripped = line.strip()
    if not stripped:
        return False
    if Q_LINE_RE.match(line):
        return False
    if _extract_options_from_line(line):
        return False
    if ROUND_HEADER_RE.search(line):
        return False
    if ANSWER_INSTRUCTION_RE.search(line):
        return False
    if RESEND_PROMPT_RE.search(line):
        return False
    return True


def _wrap_preserving_newlines(text: str, width: int) -> list[str]:
    if width <= 1:
        return [""]
    out: list[str] = []
    for para in (text or "").splitlines():
        if not para.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(para, width=width, break_long_words=True, break_on_hyphens=True))
    if not out:
        out = [""]
    return out


def _extract_options_from_line(line: str) -> list[Option]:
    opts: list[Option] = []

    mb = OPT_BULLET_RE.match(line)
    if mb:
        return [Option(letter=mb.group(1), label=mb.group(2).strip())]

    inline = OPT_INLINE_RE.findall(line)
    # Prefer inline parsing if we see 2+ tokens on the same line (e.g. "G) ..., H) ...").
    if len(inline) >= 2:
        for letter, label in inline:
            opts.append(Option(letter=letter, label=label.strip()))
        return opts

    m = OPT_LINE_RE.match(line)
    if m:
        # This may still contain other inline options separated by "/" or ",".
        # Try to split it if the label contains other "X)" tokens.
        letter = m.group(1)
        label = m.group(2).strip()
        inline2 = OPT_INLINE_RE.findall(line)
        if len(inline2) >= 2:
            for ltr, lbl in inline2:
                opts.append(Option(letter=ltr, label=lbl.strip()))
            return opts
        return [Option(letter=letter, label=label)]

    for letter, label in inline:
        opts.append(Option(letter=letter, label=label.strip()))

    # Shorthand meta line like: "G/H/I/J"
    if not opts:
        if re.search(r"\bG\s*/\s*H\s*/\s*I\s*/\s*J\b", line):
            for ltr in ("G", "H", "I", "J"):
                opts.append(Option(letter=ltr, label=META_FALLBACK_LABELS[ltr]))
    return opts


def parse_batch(
    lines: list[str], *, max_lookback: int = 200, allow_qref_fallback: bool = True
) -> Batch | None:
    """
    Parse the most recent spec-interview "round" with multiple questions (Q0..Q9, etc.).
    Returns a Batch if we can confidently extract questions + options.
    """
    if not lines:
        return None

    window = lines[-max_lookback:]

    q_indexes: list[int] = []
    for idx, line in enumerate(window):
        if Q_LINE_RE.match(line):
            q_indexes.append(idx)

    if not q_indexes:
        if not allow_qref_fallback:
            return None
        # Support alternate spec-interview rendering that omits "Qn — ..." headers and instead:
        # - prints bullet options like "- A) foo"
        # - ends with an instruction containing "Qn=A" (or "Qn=E: ...")
        # We'll parse this as a single-question batch.
        qid = None
        for line in reversed(window):
            mref = Q_REF_RE.search(line)
            if mref:
                qid = mref.group(1)
                break
        if not qid:
            return None

        opts: list[Option] = []
        title = ""
        for i, line in enumerate(window):
            opts.extend(_extract_options_from_line(line))
            if not title:
                # Pick the first non-empty line that looks like a prompt/question.
                if line.strip() and not line.lstrip().startswith(("-", "*")) and "elige" not in line.lower():
                    if not Q_REF_RE.search(line) and not line.strip().startswith("Responde"):
                        title = line.strip()

        opts = _dedupe_options(opts)
        letters = {o.letter for o in opts}
        if "A" not in letters or "B" not in letters:
            return None

        if not title:
            title = "Question"

        sig_material = f"{qid}|{title}|{''.join(o.letter for o in opts)}".encode("utf-8")
        signature = hashlib.sha1(sig_material).hexdigest()
        return Batch(questions=[Question(qid=qid, title=title, options=opts)], signature=signature)

    questions: list[Question] = []
    any_ab = False
    for qi, start_idx in enumerate(q_indexes):
        end_idx = q_indexes[qi + 1] if qi + 1 < len(q_indexes) else len(window)
        header = window[start_idx]
        m = Q_LINE_RE.match(header)
        if not m:
            continue
        qid = m.group(1)
        title = m.group(2).strip()

        opts: list[Option] = []
        last_opt_idx: int | None = None
        for line in window[start_idx + 1 : end_idx]:
            parsed = _extract_options_from_line(line)
            if parsed:
                opts.extend(parsed)
                last_opt_idx = len(opts) - 1
                continue
            if last_opt_idx is not None and _is_option_continuation_line(line):
                prev = opts[last_opt_idx]
                merged = f"{prev.label} {line.strip()}".strip()
                opts[last_opt_idx] = Option(letter=prev.letter, label=merged)

        opts = _dedupe_options(opts)
        letters = {o.letter for o in opts}
        has_ab = ("A" in letters) and ("B" in letters)
        any_ab = any_ab or has_ab
        # If this question doesn't have real A/B options, still keep it in the batch
        # as a manual-answer prompt, as long as at least one question in the overall
        # batch has credible A/B options (checked below).
        if not has_ab:
            opts = []

        questions.append(Question(qid=qid, title=title, options=opts))

    if not questions:
        return None
    if not any_ab:
        return None

    sig_material = "\n".join(
        f"{q.qid}|{q.title}|{''.join(o.letter for o in q.options)}" for q in questions
    ).encode("utf-8")
    signature = hashlib.sha1(sig_material).hexdigest()
    return Batch(questions=questions, signature=signature)


def build_pair(qid: str, letter: str, extra: str | None = None) -> str:
    if letter in {"E", "H"}:
        if extra is None:
            raise ValueError(f"{qid}={letter} requires extra text")
        # The spec-interview skill requires answers in a single line. If the user
        # entered multiline text (supported by the curses editor), encode newlines
        # safely without changing the Qn=E:/Qn=H: format.
        extra = extra.replace("\r\n", "\n").replace("\r", "\n")
        if "\n" in extra:
            extra = "\\n".join(ln.rstrip() for ln in extra.split("\n")).strip()
        return f"{qid}={letter}: {extra}"
    return f"{qid}={letter}"


def format_answer_line(pairs: list[str]) -> str:
    return ", ".join(pairs)


def _send_enter(master_fd: int, line: str) -> None:
    """
    Send a line to the child PTY as if the user typed it and pressed Enter.
    Send CR (carriage return) as the Enter key. Most TTY apps in raw mode map Enter
    to CR; sending LF can be treated as a literal newline in some prompts without
    triggering submit.
    """
    os.write(master_fd, (line + "\r").encode("utf-8"))


def _normalize_choice_input(raw: str) -> str:
    """
    Normalize raw user input for letter-picking prompts.

    - Strips ANSI/terminal control sequences (so arrow keys don't become letters).
    - Returns a cleaned string suitable for parsing.
    """
    return strip_ansi(raw).strip()


def _parse_choice_letter(cleaned: str) -> str | None:
    """
    Parse a single choice letter (A-J) from a cleaned prompt input.
    Returns the uppercase letter or None if not found.
    """
    if not cleaned:
        return None
    m = re.search(r"[A-Ja-j]", cleaned)
    if not m:
        return None
    return m.group(0).upper()


def pick_option_prompt(question: Question) -> Option:
    print(f"\n{question.qid} — {question.title}\n", file=sys.stderr)
    for opt in question.options:
        print(f"{opt.letter}) {opt.label}", file=sys.stderr)
    while True:
        try:
            raw = input(f"{question.qid} (elige letra A-J, q=cancel): ")
        except EOFError:
            raise UserCanceled()
        cleaned = _normalize_choice_input(raw)
        if cleaned.lower() == "q":
            raise UserCanceled()
        if not cleaned:
            continue
        letter = _parse_choice_letter(cleaned)
        if not letter:
            print("Letra inválida.", file=sys.stderr)
            continue
        for opt in question.options:
            if opt.letter == letter:
                return opt
        print("Letra inválida.", file=sys.stderr)


def _set_nonblocking(fd: int) -> int:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    return flags


def _restore_flags(fd: int, flags: int) -> None:
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
    except Exception:
        return


def _read_codex_until_resend(
    master_fd: int,
    *,
    settle_sec: float,
    max_sec: float = 25.0,
    debug: bool = False,
    require_resend: bool = True,
    ignore_line_prefix: str | None = None,
    quiet_after_sec: float | None = None,
) -> tuple[list[str], str]:
    """
    Read from the child PTY (master_fd) until we detect a "resend answers" prompt,
    then keep draining until output settles for settle_sec.
    Returns (stripped_lines, raw_text).
    """
    sel = selectors.DefaultSelector()
    sel.register(master_fd, selectors.EVENT_READ)
    decoder = codecs.getincrementaldecoder("utf-8")("ignore")
    orig_flags = _set_nonblocking(master_fd)

    started = time.time()
    last_data = started
    saw_resend = False
    saw_any = False
    effective_lines = 0

    raw_parts: list[str] = []
    stripped_lines: list[str] = []
    partial = ""

    try:
        while True:
            now = time.time()
            if now - started > max_sec:
                if debug:
                    print("[wrapper] meta wait timeout", file=sys.stderr)
                break

            timeout = 0.1
            events = sel.select(timeout=timeout)
            if not events:
                quiet_needed = quiet_after_sec if quiet_after_sec is not None else settle_sec
                if require_resend:
                    if saw_resend and (time.time() - last_data) >= settle_sec:
                        break
                else:
                    if saw_any and (time.time() - last_data) >= quiet_needed:
                        break
                continue

            for _key, _mask in events:
                try:
                    data = os.read(master_fd, 4096)
                except BlockingIOError:
                    data = b""
                if not data:
                    continue
                last_data = time.time()
                decoded_out = decoder.decode(data)
                if decoded_out:
                    saw_any = True
                    raw_parts.append(decoded_out)
                    clean = strip_ansi(decoded_out).replace("\r", "\n")
                    partial += clean
                    while "\n" in partial:
                        line, partial = partial.split("\n", 1)
                        if not line.strip():
                            continue
                        if ignore_line_prefix:
                            s = line.strip()
                            if s.startswith(ignore_line_prefix):
                                # Skip echoes / status repaints for the line we just sent,
                                # so we don't treat them as "real content" and return too early.
                                continue
                        stripped_lines.append(line)
                        effective_lines += 1
                        if RESEND_PROMPT_RE.search(line):
                            saw_resend = True
            if ignore_line_prefix:
                saw_any = effective_lines > 0
    finally:
        _restore_flags(master_fd, orig_flags)

    # Flush any trailing partial line
    if partial.strip():
        tail = partial.strip()
        if not (ignore_line_prefix and tail.startswith(ignore_line_prefix)):
            stripped_lines.append(tail)

    return stripped_lines, "".join(raw_parts)


def _curses_view_text(stdscr, title: str, body: str) -> None:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _drain_extra_enter_keys(stdscr)

    top = 0
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        content_w = max(10, w - 2)

        stdscr.addnstr(0, 0, title, max(0, w - 1), curses.A_BOLD)
        stdscr.addnstr(
            1,
            0,
            "↑/↓ scroll • PgUp/PgDn • Enter/d/Esc/q cerrar",
            max(0, w - 1),
        )

        lines = _wrap_preserving_newlines(body, width=content_w)
        view_h = max(1, h - 3)
        top = max(0, min(top, max(0, len(lines) - view_h)))
        slice_lines = lines[top : top + view_h]
        for i, ln in enumerate(slice_lines):
            stdscr.addnstr(2 + i, 0, ln, max(0, w - 1))

        stdscr.refresh()
        ch = stdscr.getch()
        if ch in _DETAIL_CLOSE_KEYS:
            _drain_extra_enter_keys(stdscr)
            return
        if ch in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            top = min(max(0, len(lines) - view_h), top + 1)
        elif ch == curses.KEY_NPAGE:
            top = min(max(0, len(lines) - view_h), top + view_h)
        elif ch == curses.KEY_PPAGE:
            top = max(0, top - view_h)


def _build_compare_pairs(question: Question) -> list[str]:
    letters: list[str] = []
    for opt in question.options:
        if opt.letter in {"A", "B", "C", "D"} and opt.letter not in letters:
            letters.append(opt.letter)
    pairs: list[str] = []
    for i, left in enumerate(letters):
        for right in letters[i + 1 :]:
            pairs.append(f"{left} vs {right}")
    return pairs


def _prompt_compare_text(qid: str) -> str:
    while True:
        raw = input(f"{qid} Compare (ej: A vs C): ").strip()
        if _normalize_choice_input(raw).lower() == "q":
            raise UserCanceled()
        if raw:
            return raw


def _curses_text_input(stdscr, prompt: str) -> str:
    h, w = stdscr.getmaxyx()
    prompt_line = prompt.strip()
    stdscr.addnstr(h - 2, 0, prompt_line, max(0, w - 1), curses.A_BOLD)
    stdscr.clrtoeol()

    box_w = max(10, w - 1)
    win = curses.newwin(1, box_w, h - 1, 0)
    win.keypad(True)
    win.erase()
    win.refresh()

    tb = curses.textpad.Textbox(win)
    curses.curs_set(1)
    # NOTE: Do NOT enable curses.echo() here.
    # Textbox.do_command() is responsible for rendering edits; enabling echo causes
    # each keystroke to be echoed twice in many terminals/PTY setups.

    while True:
        ch = win.getch()
        if ch in (27, ord("q")):
            curses.curs_set(0)
            raise UserCanceled()
        if ch in _ENTER_KEYS:
            _drain_extra_enter_keys(win)
            break

        # Many terminals send DEL (127) for backspace/delete. curses.textpad.Textbox
        # doesn't treat 127 as backspace, so map it to BS.
        if ch == 127:
            ch = curses.ascii.BS
        # "Delete" key is often KEY_DC; Textbox doesn't handle it, but ^d does delch().
        if ch == curses.KEY_DC:
            ch = curses.ascii.EOT
        tb.do_command(ch)

    curses.curs_set(0)
    stdscr.move(h - 2, 0)
    stdscr.clrtoeol()
    stdscr.move(h - 1, 0)
    stdscr.clrtoeol()
    stdscr.refresh()
    return tb.gather().strip()


def _curses_multiline_input(stdscr, prompt: str) -> str:
    """
    Multiline text editor:
      - Enter inserts newline
      - Ctrl+G confirms (curses.textpad convention)
      - Esc/q cancels
    """
    curses.curs_set(1)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _drain_extra_enter_keys(stdscr)

    h, w = stdscr.getmaxyx()
    title = prompt.strip()
    stdscr.erase()
    stdscr.addnstr(0, 0, title, max(0, w - 1), curses.A_BOLD)
    stdscr.addnstr(
        1,
        0,
        "Ctrl+G confirmar • Enter newline • Esc/q cancelar",
        max(0, w - 1),
    )
    stdscr.refresh()

    box_top = 2
    box_h = max(3, h - box_top - 1)
    box_w = max(10, w - 1)
    win = curses.newwin(box_h, box_w, box_top, 0)
    win.keypad(True)
    win.erase()
    win.refresh()

    tb = curses.textpad.Textbox(win)
    # NOTE: Do NOT enable curses.echo() here; Textbox handles rendering.

    while True:
        ch = win.getch()
        if ch in (27, ord("q")):
            curses.curs_set(0)
            raise UserCanceled()
        if ch == curses.ascii.BEL:  # Ctrl+G
            break

        # Many terminals send DEL (127) for backspace/delete.
        if ch == 127:
            ch = curses.ascii.BS
        # "Delete" key is often KEY_DC; Textbox doesn't handle it, but ^d does delch().
        if ch == curses.KEY_DC:
            ch = curses.ascii.EOT

        tb.do_command(ch)

    curses.curs_set(0)
    text = tb.gather().replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()

    stdscr.erase()
    stdscr.refresh()
    _drain_extra_enter_keys(stdscr)
    return "\n".join(lines).strip()


def pick_compare_prompt(question: Question) -> str:
    pairs = _build_compare_pairs(question)
    if not pairs:
        return _prompt_compare_text(question.qid)

    print(f"\n{question.qid} — Compare\n", file=sys.stderr)
    for idx, pair in enumerate(pairs, start=1):
        print(f"{idx}) {pair}", file=sys.stderr)
    other_idx = len(pairs) + 1
    print(f"{other_idx}) Other (write)", file=sys.stderr)

    while True:
        raw = input(f"{question.qid} (elige 1-{other_idx}, q=cancel): ").strip()
        cleaned = _normalize_choice_input(raw)
        if cleaned.lower() == "q":
            raise UserCanceled()
        if not cleaned:
            continue
        if cleaned.isdigit():
            choice = int(cleaned)
            if 1 <= choice <= len(pairs):
                return pairs[choice - 1]
            if choice == other_idx:
                return _prompt_compare_text(question.qid)
        print("Opción inválida.", file=sys.stderr)


def _prompt_manual_answer(qid: str) -> str:
    while True:
        raw = input(
            f"{qid} (respuesta: A-J o 'E: texto' / 'H: A vs C', q=cancel): "
        ).strip()
        cleaned = _normalize_choice_input(raw)
        if cleaned.lower() == "q":
            raise UserCanceled()
        if not cleaned:
            continue
        upper = cleaned.upper()
        if upper.startswith(f"{qid.upper()}="):
            cleaned = cleaned[len(qid) + 1 :].strip()
        m = re.match(r"^([A-Ja-j])(?:\s*[:=]\s*(.+))?$", cleaned)
        if not m:
            print("Formato inválido.", file=sys.stderr)
            continue
        letter = m.group(1).upper()
        extra = m.group(2).strip() if m.group(2) else None
        try:
            return build_pair(qid, letter, extra)
        except ValueError:
            print("Falta texto extra para esa opción.", file=sys.stderr)


def _parse_manual_answer_text(qid: str, raw: str) -> Answer:
    """
    Parse a manual answer entry like:
      - A
      - E: texto
      - H: A vs C
      - Q0=A (or Q0=E: texto)
    """
    cleaned = _normalize_choice_input(raw)
    if not cleaned:
        raise ValueError("empty")
    upper = cleaned.upper()
    if upper.startswith(f"{qid.upper()}="):
        cleaned = cleaned[len(qid) + 1 :].strip()
    m = re.match(r"^([A-Ja-j])(?:\s*[:=]\s*(.+))?$", cleaned)
    if not m:
        raise ValueError("bad format")
    letter = m.group(1).upper()
    extra = m.group(2).strip() if m.group(2) else None
    if letter in {"E", "H"} and not extra:
        raise ValueError("missing extra")
    return Answer(letter=letter, extra=extra)


def _curses_pick_answer(stdscr, question: Question) -> Answer:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _drain_extra_enter_keys(stdscr)

    options = question.options
    if not options:
        raise RuntimeError('No options to pick from')

    idx = 0
    top = 0
    show_full = False

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        header = f'{question.qid} — {question.title}'
        stdscr.addnstr(0, 0, header, max(0, w - 1), curses.A_BOLD)
        stdscr.addnstr(
            1,
            0,
            '↑/↓ seleccionar • Enter elegir • d detalles • Esc/q cancelar',
            max(0, w - 1),
        )

        visible_h = max(1, h - 3)
        if idx < top:
            top = idx
        if idx >= top + visible_h:
            top = idx - visible_h + 1

        slice_opts = options[top : top + visible_h]
        for row, opt in enumerate(slice_opts):
            abs_i = top + row
            label = opt.label if show_full else _compact_label(opt.label, max(0, w - 6))
            line = f"{opt.letter}) {label}"
            attr = curses.A_REVERSE if abs_i == idx else curses.A_NORMAL
            stdscr.addnstr(2 + row, 0, line, max(0, w - 1), attr)

        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (curses.KEY_UP, ord('k')):
            idx = (idx - 1) % len(options)
        elif ch in (curses.KEY_DOWN, ord('j')):
            idx = (idx + 1) % len(options)
        elif ch in (10, 13, curses.KEY_ENTER):
            picked = options[idx]
            if picked.letter == 'E':
                while True:
                    extra = _curses_multiline_input(stdscr, f"{question.qid} Other:")
                    if extra:
                        _drain_extra_enter_keys(stdscr)
                        return Answer(letter='E', extra=extra)
            if picked.letter == 'H':
                while True:
                    pairs = _build_compare_pairs(question)
                    if pairs:
                        # Provide a quick picker for the common A-D pairwise comparisons,
                        # plus an escape hatch for custom multi-option comparisons.
                        choice = _curses_pick_list(
                            stdscr,
                            f"{question.qid} — Compare",
                            pairs + ["Other (write)"],
                        )
                        if choice < len(pairs):
                            extra = pairs[choice]
                        else:
                            extra = _curses_multiline_input(
                                stdscr, f"{question.qid} Compare (ej: A vs C): "
                            )
                    else:
                        extra = _curses_multiline_input(
                            stdscr, f"{question.qid} Compare (ej: A vs C): "
                        )
                    if extra:
                        _drain_extra_enter_keys(stdscr)
                        return Answer(letter='H', extra=extra)
            return Answer(letter=picked.letter, extra=None)
        elif ch in (27, ord('q')):
            raise UserCanceled()
        elif ch in (ord('d'), ord('D')):
            picked = options[idx]
            _curses_view_text(
                stdscr,
                f"{question.qid} — detalle",
                f"{question.qid} — {question.title}\n\n{picked.letter}) {picked.label}",
            )


def pick_answer_curses(question: Question) -> Answer:
    return curses.wrapper(lambda stdscr: _curses_pick_answer(stdscr, question))


def _curses_pick_list(stdscr, title: str, options: list[str]) -> int:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _drain_extra_enter_keys(stdscr)

    idx = 0
    top = 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        stdscr.addnstr(0, 0, title, max(0, w - 1), curses.A_BOLD)
        stdscr.addnstr(
            1, 0, "↑/↓ seleccionar • Enter elegir • Esc/q cancelar", max(0, w - 1)
        )

        visible_h = max(1, h - 3)
        if idx < top:
            top = idx
        if idx >= top + visible_h:
            top = idx - visible_h + 1

        slice_opts = options[top : top + visible_h]
        for row, label in enumerate(slice_opts):
            abs_i = top + row
            line = f"{abs_i + 1}) {label}"
            attr = curses.A_REVERSE if abs_i == idx else curses.A_NORMAL
            stdscr.addnstr(2 + row, 0, line, max(0, w - 1), attr)

        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(options)
        elif ch in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(options)
        elif ch in (10, 13, curses.KEY_ENTER):
            _drain_extra_enter_keys(stdscr)
            return idx
        elif ch in (27, ord("q")):
            raise UserCanceled()


def _curses_draw_batch(
    stdscr,
    batch: Batch,
    *,
    answers: dict[str, Answer],
    current_index: int,
    reader_top: int,
    pending_letter: str | None,
    status_msg: str | None,
) -> tuple[int, int, int]:
    def fmt_ans_short(ans: Answer | None) -> str:
        if ans is None:
            return "_"
        return ans.letter

    def build_scoreboard_text() -> str:
        parts: list[str] = []
        for q in batch.questions:
            parts.append(f"{q.qid}={fmt_ans_short(answers.get(q.qid))}")
        return " ".join(parts)

    def build_reader_lines(
        question: Question, *, width: int, pending: str | None
    ) -> list[tuple[str, int]]:
        out: list[tuple[str, int]] = []
        qhdr = f"{question.qid} — {question.title}".strip()
        for ln in _wrap_preserving_newlines(qhdr, width=width):
            out.append((ln, curses.A_BOLD))
        out.append(("", curses.A_NORMAL))

        if not question.options:
            out.append(("(sin opciones: se pedirá texto)", curses.A_DIM))
            return out

        for opt in question.options:
            is_pending = pending is not None and opt.letter == pending
            marker = "▶" if is_pending else " "
            prefix = f"{marker} {opt.letter}) "
            avail = max(1, width - len(prefix))
            wrapped = _wrap_preserving_newlines(opt.label, width=avail)
            attr = curses.A_REVERSE if is_pending else curses.A_NORMAL

            out.append((prefix + (wrapped[0] if wrapped else ""), attr))
            indent = " " * len(prefix)
            for ln in wrapped[1:]:
                out.append((indent + ln, attr))
            out.append(("", curses.A_NORMAL))
        return out

    stdscr.erase()
    h, w = stdscr.getmaxyx()

    current_q = batch.questions[current_index]
    total = len(batch.questions)
    answered = len(answers)
    pending_txt = pending_letter or "-"
    progress = f"Batch {current_index + 1}/{total} • Respondidas {answered}/{total} • Pendiente: {pending_txt}"

    hint = "Opciones ↑/↓ (wrap) • Scroll PgUp/PgDn Home/End • Elegir A–J • Enter confirmar • d detalle • q/Esc cancelar"

    top_lines: list[str] = [progress, hint]
    if status_msg:
        top_lines.append(status_msg)

    scoreboard = build_scoreboard_text()
    scoreboard_lines = textwrap.wrap(scoreboard, width=max(1, w - 1)) if scoreboard else []
    top_lines.extend(scoreboard_lines)

    # Compact top area to the amount of real content to avoid large empty gaps.
    min_top_content = 2  # progress + hints
    min_bottom = 4
    max_sep = max(min_top_content, h - (min_bottom + 1))
    sep_y = max(min_top_content, min(len(top_lines), max_sep))
    bottom_y = min(h - 1, sep_y + 1)
    bottom_h = max(1, h - bottom_y)
    top_h = sep_y

    for i in range(min(top_h, len(top_lines))):
        attr = curses.A_BOLD if (i == 0 or (status_msg and i == 2)) else curses.A_NORMAL
        stdscr.addnstr(i, 0, top_lines[i], max(0, w - 1), attr)

    if 0 <= sep_y < h:
        stdscr.hline(sep_y, 0, curses.ACS_HLINE, max(0, w - 1))

    content_w = max(1, w - 2)
    reader_lines = build_reader_lines(current_q, width=content_w, pending=pending_letter)
    max_top = max(0, len(reader_lines) - bottom_h)
    reader_top = max(0, min(reader_top, max_top))

    slice_lines = reader_lines[reader_top : reader_top + bottom_h]
    for i, (ln, attr) in enumerate(slice_lines):
        stdscr.addnstr(bottom_y + i, 0, ln, max(0, w - 1), attr)

    stdscr.refresh()
    return reader_top, max_top, bottom_h


def _curses_help_and_answer(
    stdscr,
    *,
    master_fd: int,
    question: Question,
    initial_meta_line: str,
    settle_sec: float,
    debug: bool,
) -> Answer:
    """
    Execute one meta request (G/H/I/J) for a question, show the resulting Codex help
    in a top pane, and require answering the question (A-F/E) in the bottom pane.

    The user can request additional meta help again from this screen.
    """
    help_lines: list[str] = []

    def run_meta(meta_line: str) -> None:
        os.write(master_fd, (meta_line + "\r").encode("utf-8"))
        lines, _raw = _read_codex_until_resend(
            master_fd,
            settle_sec=settle_sec,
            max_sec=25.0,
            debug=debug,
            require_resend=False,
            ignore_line_prefix=meta_line,
            quiet_after_sec=max(settle_sec, 1.0),
        )
        help_lines.extend(lines)
        # While Codex is producing the meta/help response, users often press Enter to "continue".
        # If that leaks into this screen, it can select an option immediately and accidentally
        # advance/answer. Drop only CR/LF typeahead here.
        _drain_extra_enter_keys(stdscr)

    # First meta request (the one the user selected in the batch picker)
    run_meta(initial_meta_line)

    # Filter real answer options vs meta options (meta stay available as actions).
    options = question.options
    if not options:
        raise RuntimeError("No options to pick from")

    opt_idx = 0
    opt_top = 0
    help_top = 0
    focus = "options"  # "help" | "options"

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        stdscr.keypad(True)
        curses.curs_set(0)

        stdscr.addnstr(
            0,
            0,
            f"{question.qid} — ayuda + respuesta",
            max(0, w - 1),
            curses.A_BOLD,
        )
        stdscr.addnstr(
            1,
            0,
            "Tab foco • ↑/↓ navegar • PgUp/PgDn scroll ayuda • Enter elegir • d detalle • q/Esc cancelar",
            max(0, w - 1),
        )

        # Layout: help pane (top) + separator + options pane (bottom)
        min_opt_h = 7
        opt_h = min(max(min_opt_h, h // 3), max(min_opt_h, h - 6))
        help_h = max(1, h - opt_h - 4)

        help_attr = curses.A_REVERSE if focus == "help" else curses.A_NORMAL
        opt_attr = curses.A_REVERSE if focus == "options" else curses.A_NORMAL

        stdscr.addnstr(2, 0, "Ayuda (Codex):", max(0, w - 1), help_attr)

        help_text = "\n".join(help_lines) if help_lines else "(sin ayuda capturada)"
        wrapped = _wrap_preserving_newlines(help_text, width=max(10, w - 2))
        view_h = help_h
        help_top = max(0, min(help_top, max(0, len(wrapped) - view_h)))
        slice_lines = wrapped[help_top : help_top + view_h]
        for i, ln in enumerate(slice_lines):
            stdscr.addnstr(3 + i, 0, ln, max(0, w - 1))

        sep_y = 3 + help_h
        if sep_y < h:
            stdscr.hline(sep_y, 0, curses.ACS_HLINE, max(0, w - 1))

        q_y = sep_y + 1
        if q_y < h:
            stdscr.addnstr(
                q_y,
                0,
                f"{question.qid} — {question.title}",
                max(0, w - 1),
                curses.A_BOLD,
            )

        list_top = q_y + 1
        list_h = max(1, h - list_top - 1)
        if opt_idx < opt_top:
            opt_top = opt_idx
        if opt_idx >= opt_top + list_h:
            opt_top = opt_idx - list_h + 1

        for row, opt in enumerate(options[opt_top : opt_top + list_h]):
            abs_i = opt_top + row
            line = f"{opt.letter}) {_compact_label(opt.label, max(0, w - 6))}"
            attr = opt_attr if (focus == "options" and abs_i == opt_idx) else curses.A_NORMAL
            stdscr.addnstr(list_top + row, 0, line, max(0, w - 1), attr)

        stdscr.refresh()
        ch = stdscr.getch()

        if ch in (27, ord("q")):
            raise UserCanceled()
        if ch == 9:  # Tab
            focus = "help" if focus == "options" else "options"
            continue

        if ch in (ord("d"), ord("D")):
            picked = options[opt_idx]
            _curses_view_text(
                stdscr,
                f"{question.qid} — detalle",
                f"{question.qid} — {question.title}\n\n{picked.letter}) {picked.label}",
            )
            continue

        if focus == "help":
            if ch in (curses.KEY_UP, ord("k")):
                help_top = max(0, help_top - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                help_top = min(max(0, len(wrapped) - view_h), help_top + 1)
            elif ch == curses.KEY_NPAGE:
                help_top = min(max(0, len(wrapped) - view_h), help_top + view_h)
            elif ch == curses.KEY_PPAGE:
                help_top = max(0, help_top - view_h)
            continue

        # focus == "options"
        if ch in (curses.KEY_UP, ord("k")):
            opt_idx = (opt_idx - 1) % len(options)
        elif ch in (curses.KEY_DOWN, ord("j")):
            opt_idx = (opt_idx + 1) % len(options)
        elif ch in _ENTER_KEYS:
            picked = options[opt_idx]
            # Meta actions: request more help and stay on this screen.
            if picked.letter in _META_LETTERS:
                if picked.letter == "H":
                    pairs = _build_compare_pairs(question)
                    if pairs:
                        choice = _curses_pick_list(
                            stdscr,
                            f"{question.qid} — Compare",
                            pairs + ["Other (write)"],
                        )
                        if choice < len(pairs):
                            extra = pairs[choice]
                        else:
                            extra = _curses_multiline_input(
                                stdscr, f"{question.qid} Compare (ej: A vs C): "
                            )
                    else:
                        extra = _curses_multiline_input(
                            stdscr, f"{question.qid} Compare (ej: A vs C): "
                        )
                    if extra:
                        run_meta(build_pair(question.qid, "H", extra))
                else:
                    run_meta(build_pair(question.qid, picked.letter, None))
                continue

            # Real answers
            if picked.letter == "E":
                while True:
                    extra = _curses_multiline_input(stdscr, f"{question.qid} Other:")
                    if extra:
                        _drain_extra_enter_keys(stdscr)
                        return Answer(letter="E", extra=extra)
            if picked.letter == "H":
                # In spec-interview, H is meta; but if it ever appears as an answer option,
                # keep compatibility by requiring extra.
                while True:
                    extra = _curses_multiline_input(stdscr, f"{question.qid} H:")
                    if extra:
                        _drain_extra_enter_keys(stdscr)
                        return Answer(letter="H", extra=extra)
            _drain_extra_enter_keys(stdscr)
            return Answer(letter=picked.letter, extra=None)
        else:
            if 0 <= ch <= 255:
                c = chr(ch).upper()
                if "A" <= c <= "J":
                    for i, opt in enumerate(options):
                        if opt.letter == c:
                            opt_idx = i
                            break


def _curses_pick_batch(
    stdscr,
    *,
    batch: Batch,
    master_fd: int,
    settle_sec: float,
    debug: bool,
) -> dict[str, Answer]:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _drain_extra_enter_keys(stdscr)

    answers: dict[str, Answer] = {}
    current_index = 0
    reader_top = 0
    pending_letter: str | None = None
    status_msg: str | None = None

    def default_pending_for(question: Question) -> str | None:
        if not question.options:
            return None
        letters = [o.letter for o in question.options]
        if "A" in letters:
            return "A"
        return letters[0]

    def cycle_pending_for(question: Question, current: str | None, delta: int) -> str | None:
        if not question.options:
            return None
        letters = [o.letter for o in question.options]
        if not letters:
            return current
        if current not in letters:
            return letters[0] if delta > 0 else letters[-1]
        idx = letters.index(current)
        return letters[(idx + delta) % len(letters)]

    while current_index < len(batch.questions):
        q = batch.questions[current_index]
        if pending_letter is None:
            pending_letter = default_pending_for(q)

        if not q.options:
            err: str | None = None
            base_prompt = f"{q.qid} (A-J o 'E: texto' / 'H: A vs C'): "
            while True:
                prompt = base_prompt if not err else f"{base_prompt} [Formato inválido]"
                raw = _curses_text_input(stdscr, prompt)
                if not raw:
                    continue
                try:
                    ans = _parse_manual_answer_text(q.qid, raw)
                except ValueError:
                    err = "bad"
                    curses.beep()
                    continue
                answers[q.qid] = ans
                _drain_extra_enter_keys(stdscr)
                current_index += 1
                reader_top = 0
                pending_letter = None
                break
            continue

        reader_top, max_reader_top, page_h = _curses_draw_batch(
            stdscr,
            batch,
            answers=answers,
            current_index=current_index,
            reader_top=reader_top,
            pending_letter=pending_letter,
            status_msg=status_msg,
        )
        status_msg = None

        ch = stdscr.getch()
        if ch == curses.KEY_RESIZE:
            continue

        # Option navigation with arrows (wrap-around). Reader scroll uses PgUp/PgDn/Home/End.
        if ch == curses.KEY_UP:
            pending_letter = cycle_pending_for(q, pending_letter, -1)
            status_msg = None
        elif ch == curses.KEY_DOWN:
            pending_letter = cycle_pending_for(q, pending_letter, +1)
            status_msg = None
        # Scroll keys (reader-only)
        elif ch == ord("k"):
            reader_top = max(0, reader_top - 1)
        elif ch == ord("j"):
            reader_top = min(max_reader_top, reader_top + 1)
        elif ch == curses.KEY_NPAGE:  # PgDn
            reader_top = min(max_reader_top, reader_top + max(1, page_h))
        elif ch == curses.KEY_PPAGE:  # PgUp
            reader_top = max(0, reader_top - max(1, page_h))
        elif ch == curses.KEY_HOME:
            reader_top = 0
        elif ch == curses.KEY_END:
            reader_top = max_reader_top
        elif ch in (27, ord("q")):
            raise UserCanceled()
        elif ch in (ord("d"), ord("D")):
            if not pending_letter:
                status_msg = "Primero seleccioná A–J (pendiente)."
                curses.beep()
            else:
                picked = next((o for o in q.options if o.letter == pending_letter), None)
                if not picked:
                    status_msg = "Selección inválida."
                    curses.beep()
                else:
                    _curses_view_text(
                        stdscr,
                        f"{q.qid} — detalle",
                        f"{q.qid} — {q.title}\n\n{picked.letter}) {picked.label}",
                    )
        elif ch in _ENTER_KEYS:
            if not pending_letter:
                status_msg = "Elegí una opción A–J y luego Enter."
                curses.beep()
                continue
            picked = next((o for o in q.options if o.letter == pending_letter), None)
            if not picked:
                status_msg = "Selección inválida."
                curses.beep()
                continue
            if picked.letter in _META_LETTERS:
                # Meta help: send Qn=G/H/I/J, capture Codex explanation inside UI,
                # then force answering this question before continuing.
                if picked.letter == "H":
                    pairs = _build_compare_pairs(q)
                    if pairs:
                        choice = _curses_pick_list(
                            stdscr, f"{q.qid} — Compare", pairs + ["Other (write)"]
                        )
                        if choice < len(pairs):
                            extra = pairs[choice]
                        else:
                            extra = _curses_multiline_input(
                                stdscr, f"{q.qid} Compare (ej: A vs C): "
                            )
                    else:
                        extra = _curses_multiline_input(
                            stdscr, f"{q.qid} Compare (ej: A vs C): "
                        )
                    if not extra:
                        status_msg = "Compare requiere texto."
                        continue
                    meta_line = build_pair(q.qid, "H", extra)
                else:
                    meta_line = build_pair(q.qid, picked.letter, None)

                ans = _curses_help_and_answer(
                    stdscr,
                    master_fd=master_fd,
                    question=q,
                    initial_meta_line=meta_line,
                    settle_sec=settle_sec,
                    debug=debug,
                )
                answers[q.qid] = ans
                _drain_extra_enter_keys(stdscr)
                current_index += 1
                reader_top = 0
                pending_letter = None
            elif picked.letter == "E":
                while True:
                    extra = _curses_multiline_input(stdscr, f"{q.qid} Other:")
                    if not extra:
                        status_msg = "Other requiere texto."
                        break
                    answers[q.qid] = Answer(letter="E", extra=extra)
                    _drain_extra_enter_keys(stdscr)
                    current_index += 1
                    reader_top = 0
                    pending_letter = None
                    break
            elif picked.letter == "H":
                pairs = _build_compare_pairs(q)
                if pairs:
                    choice = _curses_pick_list(stdscr, f"{q.qid} — Compare", pairs + ["Other (write)"])
                    if choice < len(pairs):
                        extra = pairs[choice]
                    else:
                        extra = _curses_multiline_input(stdscr, f"{q.qid} Compare (ej: A vs C): ")
                else:
                    extra = _curses_multiline_input(stdscr, f"{q.qid} Compare (ej: A vs C): ")
                if not extra:
                    status_msg = "Compare requiere texto."
                else:
                    answers[q.qid] = Answer(letter="H", extra=extra)
                    _drain_extra_enter_keys(stdscr)
                    current_index += 1
                    reader_top = 0
                    pending_letter = None
            else:
                answers[q.qid] = Answer(letter=picked.letter, extra=None)
                _drain_extra_enter_keys(stdscr)
                current_index += 1
                reader_top = 0
                pending_letter = None
        else:
            if 0 <= ch <= 255:
                c = chr(ch).upper()
                if "A" <= c <= "J":
                    pending_letter = c
                    status_msg = None

    return answers


def pick_batch_curses(
    batch: Batch,
    *,
    master_fd: int,
    settle_sec: float,
    debug: bool,
) -> dict[str, Answer]:
    """
    Curses UI picker for a full batch. Supports inline meta help (G/H/I/J):
    it captures Codex explanations from master_fd and shows them inside the UI.
    """
    return curses.wrapper(
        lambda stdscr: _curses_pick_batch(
            stdscr, batch=batch, master_fd=master_fd, settle_sec=settle_sec, debug=debug
        )
    )


class TerminalController:
    def __init__(self, fd: int):
        self.fd = fd
        self._orig = termios.tcgetattr(fd)
        self._raw = False

    def flush_input(self) -> None:
        try:
            termios.tcflush(self.fd, termios.TCIFLUSH)
        except Exception:
            return

    def set_raw(self) -> None:
        tty.setraw(self.fd)
        self._raw = True

    def restore(self) -> None:
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self._orig)
        self._raw = False

    @contextmanager
    def cooked(self):
        was_raw = self._raw
        if was_raw:
            self.restore()
        # Discard queued keystrokes/newlines so we don't immediately re-prompt.
        self.flush_input()
        try:
            yield
        finally:
            # Discard any queued keys that some terminals send as "extra" Enter
            # (e.g. CRLF). Otherwise those can leak into the child PTY as a blank
            # submit right after the UI closes.
            self.flush_input()
            if was_raw:
                self.set_raw()


def _best_effort_restore_terminal(terminal: TerminalController) -> None:
    """
    Best-effort restore of the current TTY.

    This wrapper toggles stdin into raw mode; if the process is terminated
    (especially via SIGTERM/SIGINT) before normal cleanup, the outer shell can
    appear "dead" (no echo, weird line discipline). We try hard to revert.
    """
    try:
        terminal.restore()
    except Exception:
        pass
    try:
        subprocess.run(
            ["stty", "sane"],
            check=False,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except Exception:
        pass


def _spawn(*_args, **_kwargs):
    raise RuntimeError("_spawn is deprecated; use run_interactive() fork/exec path")  # pragma: no cover


def _ensure_codex_on_path() -> None:
    """
    Best-effort: make sure the Node global bin path used by sb() is visible
    when we later spawn `bash -lc 'codex ...'` inside the container.
    """
    if shutil.which("codex"):
        return

    candidates = [
        "/root/.npm-global/bin",
    ]
    existing = os.environ.get("PATH", "")
    parts = existing.split(":") if existing else []
    for d in candidates:
        if d not in parts and os.path.isdir(d):
            os.environ["PATH"] = f"{d}:{existing}" if existing else d
            existing = os.environ["PATH"]
            parts = existing.split(":")

    # Some environments set PATH in login shells and omit this in non-login shells.
    # Ensure common install locations are included.
    for d in ("/usr/local/bin", "/usr/bin", "/bin"):
        if d not in parts and os.path.isdir(d):
            os.environ["PATH"] = f"{existing}:{d}" if existing else d
            existing = os.environ["PATH"]
            parts = existing.split(":")


def _resolve_cmd(cmd: str) -> str:
    """
    If cmd starts with `codex`, resolve it to an absolute path or
    inject a PATH export so `bash -lc` doesn't lose Node global bin paths.
    """
    tokens = shlex.split(cmd)
    if not tokens:
        return cmd
    if tokens[0] != "codex":
        return cmd

    resolved = shutil.which("codex")
    if resolved:
        tokens[0] = resolved
        return shlex.join(tokens)

    # Try common locations even if PATH is missing/overridden by login shell.
    for candidate in ("/root/.npm-global/bin/codex", "/usr/local/bin/codex"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            tokens[0] = candidate
            return shlex.join(tokens)

    return cmd


def run_interactive(
    *,
    shell: str,
    cmd: str,
    login_shell: bool,
    history_lines: int,
    cooldown_sec: float,
    settle_sec: float,
    use_curses: bool,
    debug: bool,
) -> int:
    shell_flag = "-lc" if login_shell else "-c"
    full_cmd = f"{shell} {shell_flag} {cmd!r}"
    if os.environ.get("CODEX_WRAPPER_SPAWN_LOG") == "1":
        print(f"[wrapper] spawn: {full_cmd}", file=sys.stderr)
    pid, master_fd = pty.fork()
    if pid == 0:
        os.execvp(shell, [shell, shell_flag, cmd])
        raise RuntimeError("exec failed")  # pragma: no cover

    def _sync_winsize() -> None:
        """
        Make the child PTY match the current terminal size.
        Without this, many TUI apps will render as if width==1 and wrap every character.
        """
        try:
            src_fd = sys.stdout.fileno() if sys.stdout.isatty() else sys.stdin.fileno()
            winsize = fcntl.ioctl(src_fd, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            return

    _sync_winsize()
    prev_winch = signal.getsignal(signal.SIGWINCH)

    def _on_winch(_signum, _frame):
        _sync_winsize()
        try:
            os.kill(pid, signal.SIGWINCH)
        except Exception:
            pass

    signal.signal(signal.SIGWINCH, _on_winch)

    sel = selectors.DefaultSelector()
    sel.register(master_fd, selectors.EVENT_READ)
    sel.register(sys.stdin.fileno(), selectors.EVENT_READ)

    terminal = TerminalController(sys.stdin.fileno())
    terminal.set_raw()
    atexit.register(_best_effort_restore_terminal, terminal)

    prev_signal_handlers: dict[int, object] = {}

    def _signal_restore_then_exit(signum: int, _frame) -> None:
        _best_effort_restore_terminal(terminal)
        if signum == signal.SIGINT:
            raise KeyboardInterrupt()
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
        try:
            prev_signal_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, _signal_restore_then_exit)
        except Exception:
            continue

    decoder = codecs.getincrementaldecoder("utf-8")("ignore")
    partial = ""
    recent: list[str] = []
    round_buf = RoundBuffer(max_lines=max(8000, history_lines * 10))

    last_trigger = 0.0
    active_sig: str | None = None
    last_output_time = 0.0
    suppress_qref_fallback = False
    saw_resend_prompt = False
    last_batch: Batch | None = None
    dismissed_batch: Batch | None = None
    reopen_batch_requested = False
    last_user_input_time = 0.0
    # Some terminals deliver Enter as multiple events (CRLF) and/or leave a stray
    # newline in the input buffer when a curses Textbox is submitted. If we
    # forward that immediately to Codex, it gets interpreted as an extra blank
    # submit. We suppress pure newline input for a short window after closing
    # our own UI prompts.
    suppress_stdin_newline_until = 0.0

    def log(msg: str) -> None:
        if debug:
            print(msg, file=sys.stderr)

    try:
        while True:
            for key, _mask in sel.select(timeout=0.2):
                if key.fileobj == master_fd:
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError as e:
                        # When the child exits quickly (e.g. command not found),
                        # some PTY setups raise EIO instead of returning b"".
                        if getattr(e, "errno", None) == 5:
                            return 1
                        raise
                    if not data:
                        return 0
                    decoded_out = decoder.decode(data)
                    sys.stdout.write(decoded_out)
                    sys.stdout.flush()

                    chunk_text = strip_ansi(decoded_out)
                    if chunk_text:
                        last_output_time = time.time()
                        # Codex CLI often uses carriage returns to "repaint" a status line.
                        # If we treat CR as just another character, we end up concatenating
                        # unrelated UI fragments into one long line and confuse the parser/UI.
                        partial += chunk_text.replace("\r", "\n")
                        while "\n" in partial:
                            line, partial = partial.split("\n", 1)
                            if line.strip():
                                # Avoid polluting the parser buffer with Codex chrome/status lines
                                # (these frequently repaint and can get interleaved with prompts).
                                if CODEX_CHROME_RE.search(line):
                                    continue
                            if RESEND_PROMPT_RE.search(line):
                                saw_resend_prompt = True
                            recent.append(line)
                            round_buf.push_line(line)
                            if len(recent) > history_lines:
                                recent = recent[-history_lines:]

                elif key.fileobj == sys.stdin.fileno():
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        continue
                    requested, data = _consume_reopen_shortcut(
                        data, can_reopen=(dismissed_batch is not None)
                    )
                    if requested:
                        reopen_batch_requested = True
                        log("[wrapper] reopen shortcut requested (Ctrl+O)")
                    if not data:
                        continue
                    last_user_input_time = time.time()
                    if last_user_input_time < suppress_stdin_newline_until:
                        # Drop only pure CR/LF sequences; never drop real input.
                        if set(data) <= {10, 13}:
                            continue
                    os.write(master_fd, data)

            now = time.time()
            if now - last_trigger < cooldown_sec:
                continue

            parse_lines = round_buf.preferred_lines(recent)
            max_lookback = min(len(parse_lines), max(history_lines, 4000))
            batch = parse_batch(
                parse_lines,
                max_lookback=max_lookback,
                allow_qref_fallback=not suppress_qref_fallback,
            )
            reused_last_batch = False
            forced_reopen = False
            if not batch:
                if reopen_batch_requested and dismissed_batch is not None:
                    batch = dismissed_batch
                    reused_last_batch = True
                    forced_reopen = True
                    reopen_batch_requested = False
                    log(
                        f"[wrapper] reopening dismissed batch "
                        f"qids={[q.qid for q in batch.questions]}"
                    )
                if (
                    not batch
                    and
                    saw_resend_prompt
                    and last_batch is not None
                    and now - last_output_time >= settle_sec
                ):
                    batch = last_batch
                    saw_resend_prompt = False
                    reused_last_batch = True
                    log(
                        f"[wrapper] resend prompt detected; reusing last batch "
                        f"qids={[q.qid for q in batch.questions]}"
                    )
                else:
                    continue
            elif dismissed_batch is not None and dismissed_batch.signature != batch.signature:
                # A newly parsed batch supersedes any previously dismissed one.
                dismissed_batch = None
            # If we can parse proper "Qn — ..." headers again, we can safely re-enable
            # the Q-ref fallback mode (it was only suppressed to avoid meta-help prose).
            if suppress_qref_fallback and any(Q_LINE_RE.match(ln) for ln in parse_lines[-50:]):
                suppress_qref_fallback = False
            quiet_for = now - last_output_time
            if not reused_last_batch and not forced_reopen:
                ok, reason = _batch_completeness_gate(
                    parse_lines,
                    quiet_for=quiet_for,
                    settle_sec=settle_sec,
                    min_q_headers=2,
                )
                if not ok:
                    log(f"[wrapper] gate: {reason}")
                    continue
            # Avoid popping the picker while the user is actively typing in the Codex prompt.
            # Otherwise keystrokes/arrows can get consumed by our prompts and appear as escape codes.
            if now - last_user_input_time < 0.6:
                continue
            if active_sig == batch.signature:
                continue

            active_sig = batch.signature
            last_trigger = now
            log(
                f"[wrapper] detected batch: {len(batch.questions)} questions, "
                f"qids={[q.qid for q in batch.questions]}, sig={active_sig[:8]}"
            )

            pairs_by_qid: dict[str, str] = {}
            try:
                with terminal.cooked():
                    if use_curses and sys.stdin.isatty() and sys.stdout.isatty():
                        try:
                            # Reset decoder state before entering curses UI; we may read from
                            # master_fd inside curses for meta-help, so we want a clean boundary.
                            decoder.reset()
                            partial = ""
                            answers = pick_batch_curses(
                                batch, master_fd=master_fd, settle_sec=settle_sec, debug=debug
                            )
                        except UserCanceled:
                            raise
                        except Exception as e:
                            log(f"[wrapper] batch curses failed; falling back to prompt: {e!r}")
                            answers = {}
                        for q in batch.questions:
                            ans = answers.get(q.qid)
                            if ans is None:
                                continue
                            pairs_by_qid[q.qid] = build_pair(q.qid, ans.letter, ans.extra)
                    if not pairs_by_qid:
                        for q in batch.questions:
                            if not q.options:
                                pair = _prompt_manual_answer(q.qid)
                                pairs_by_qid[q.qid] = pair
                                continue

                            while True:
                                opt = pick_option_prompt(q)
                                if opt.letter in _META_LETTERS:
                                    if opt.letter == "H":
                                        extra = pick_compare_prompt(q)
                                        meta_line = build_pair(q.qid, "H", extra)
                                    else:
                                        meta_line = build_pair(q.qid, opt.letter, None)
                                    _send_enter(master_fd, meta_line)
                                    # In prompt mode, show Codex help in the normal terminal output.
                                    _lines, raw = _read_codex_until_resend(
                                        master_fd,
                                        settle_sec=settle_sec,
                                        max_sec=25.0,
                                        debug=debug,
                                        require_resend=False,
                                        ignore_line_prefix=meta_line,
                                        quiet_after_sec=max(settle_sec, 1.0),
                                    )
                                    if raw:
                                        sys.stdout.write(raw)
                                        sys.stdout.flush()
                                    continue

                                extra: str | None = None
                                if opt.letter == "E":
                                    extra = input(f"{q.qid} Other: ").strip()
                                elif opt.letter == "H":
                                    extra = pick_compare_prompt(q)
                                ans = Answer(letter=opt.letter, extra=extra)
                                pair = build_pair(q.qid, ans.letter, ans.extra)
                                pairs_by_qid[q.qid] = pair
                                break

                    ordered = [pairs_by_qid[q.qid] for q in batch.questions if q.qid in pairs_by_qid]
                    if len(ordered) == len(batch.questions):
                        line = format_answer_line(ordered)
                        log(f"[wrapper] send(full): {line}")
                        _send_enter(master_fd, line)
                        # Suppress any stray Enter that immediately follows UI submission.
                        suppress_stdin_newline_until = time.time() + 0.35
                        last_batch = batch
                        # Clear any previous "resend" detection so we don't immediately
                        # re-open the same batch without Codex actually asking again.
                        saw_resend_prompt = False
                        # If the user asked for meta help (explain/compare/recommend/examples),
                        # Codex typically responds with a prose block + then re-asks for answers.
                        # That prose often contains "Qn=..." instructions and bullet options,
                        # which our fallback parser can mistakenly treat as a new batch.
                        suppress_qref_fallback = bool(re.search(r"\bQ\d+\s*=\s*[GHIJ]\b", line))
                        dismissed_batch = None
                        recent.clear()
                        round_buf.reset()
                        partial = ""
                        active_sig = None
            except UserCanceled:
                log("[wrapper] canceled by user")
                dismissed_batch = batch
                print(
                    "[wrapper] UI cerrada. Presioná Ctrl+O para reabrir el último batch.",
                    file=sys.stderr,
                )
                # Suppress any stray Enter that immediately follows closing our UI.
                suppress_stdin_newline_until = time.time() + 0.35
                # Ensure any buffered question text doesn't immediately re-trigger.
                recent.clear()
                round_buf.reset()
                partial = ""
                active_sig = None
                suppress_qref_fallback = False
                saw_resend_prompt = False

            # allow re-trigger if Codex re-prints same batch after meta answer
            last_trigger = time.time()

    finally:
        _best_effort_restore_terminal(terminal)
        for sig, prev in prev_signal_handlers.items():
            try:
                signal.signal(sig, prev)
            except Exception:
                continue
        try:
            signal.signal(signal.SIGWINCH, prev_winch)
        except Exception:
            pass
        try:
            os.close(master_fd)
        except Exception:
            pass


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="TUI wrapper for Codex spec-interview rounds.")
    ap.add_argument("--shell", default="bash", help="Shell to run codex command in (default: bash)")
    ap.add_argument("--cmd", default="codex --no-alt-screen", help="Command to spawn (default: codex --no-alt-screen)")
    ap.add_argument(
        "--login-shell",
        action="store_true",
        help="Use a login shell (e.g. bash -lc). Default is non-login (bash -c) to preserve PATH.",
    )
    ap.add_argument("--history-lines", type=int, default=800)
    ap.add_argument("--cooldown-sec", type=float, default=1.0)
    ap.add_argument(
        "--settle-sec",
        type=float,
        default=0.35,
        help="Wait this long after last output before triggering batch UI (prevents mid-print detection).",
    )
    ap.add_argument("--no-curses", action="store_true", help="Disable curses UI (use prompt)")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    _ensure_codex_on_path()
    resolved_cmd = _resolve_cmd(args.cmd)

    return run_interactive(
        shell=args.shell,
        cmd=resolved_cmd,
        login_shell=args.login_shell,
        history_lines=args.history_lines,
        cooldown_sec=args.cooldown_sec,
        settle_sec=args.settle_sec,
        use_curses=not args.no_curses,
        debug=args.debug,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
