#!/usr/bin/env python3
"""
Compute TASKS progress from a TASKS.md file.

Counts:
- total: unique TaskIDs matching pattern T<number>.<number>
- done: checkbox "- [x] T?.?" OR entries under "Completed tasks:" inside Execution status

Usage:
  python scripts/tasks_progress.py docs/specs/<slug>/TASKS.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TASK_RE = re.compile(r"\b(T\d+\.\d+)\b")


def extract_total(text: str) -> int:
    return len(set(TASK_RE.findall(text)))


def extract_done(text: str) -> int:
    done: set[str] = set()

    # A) checkbox done
    for m in re.finditer(
        r"^\s*-\s*\[x\]\s*(T\d+\.\d+)\b", text, flags=re.IGNORECASE | re.MULTILINE
    ):
        done.add(m.group(1))

    # B) "Completed tasks:" list inside execution status (best-effort)
    parts = re.split(r"(?m)^\s*##\s+Execution status\s*$", text)
    if len(parts) >= 2:
        exec_block = parts[-1]
        exec_block = re.split(r"(?m)^\s*##\s+", exec_block)[0]
        if re.search(r"(?im)^\s*Completed tasks:\s*$", exec_block):
            after = re.split(r"(?im)^\s*Completed tasks:\s*$", exec_block, maxsplit=1)[1]
            for line in after.splitlines():
                if not line.strip():
                    continue
                if not re.match(r"^\s*[-*]\s+", line) and not line.startswith(" "):
                    break
                m = TASK_RE.search(line)
                if m:
                    done.add(m.group(1))

    return len(done)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/tasks_progress.py <TASKS.md>", file=sys.stderr)
        raise SystemExit(2)

    p = Path(sys.argv[1])
    if not p.exists():
        print(f"ERROR: file not found: {p}", file=sys.stderr)
        raise SystemExit(1)

    text = p.read_text(encoding="utf-8")
    total = extract_total(text)
    done = extract_done(text)

    print(f"total={total}")
    print(f"done={done}")
    print(f"remaining={max(total - done, 0)}")


if __name__ == "__main__":
    main()
