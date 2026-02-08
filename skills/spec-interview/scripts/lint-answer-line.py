#!/usr/bin/env python3
"""
Optional helper: validates spec-interview answer lines.

Examples:
  Q0=A, Q1=E: foo, Q2=F
  q1=a,q2=b
  Q3=G
"""

import re
import sys

PAIR_RE = re.compile(r"""
^
\s*
(?:
  (?:Q|q)(\d+)
  \s*=\s*
  (?:
    ([A-Fa-f])
    (?:\s*:\s*(.*?))?
    |
    ([G-Jg-j])
  )
)
\s*
$
""", re.VERBOSE)

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: lint-answer-line.py '<one line answer>'", file=sys.stderr)
        return 2

    line = sys.argv[1].strip()
    if "\n" in line or "\r" in line:
        print("ERROR: Answer must be a single line (no newlines).", file=sys.stderr)
        return 1

    parts = [p.strip() for p in line.split(",") if p.strip()]
    if not parts:
        print("ERROR: Empty answer line.", file=sys.stderr)
        return 1

    seen = set()
    for part in parts:
        m = PAIR_RE.match(part)
        if not m:
            print(f"ERROR: Invalid segment: {part!r}", file=sys.stderr)
            return 1
        qnum = int(m.group(1))
        if qnum in seen:
            print(f"ERROR: Duplicate answer for Q{qnum}.", file=sys.stderr)
            return 1
        seen.add(qnum)

        choice_af = m.group(2)
        free_text = m.group(3)
        choice_ghij = m.group(4)

        if choice_af and choice_af.upper() == "E":
            if not free_text or not free_text.strip():
                print(f"ERROR: Q{qnum}=E requires free text: 'Q{qnum}=E: <text>'.", file=sys.stderr)
                return 1

    print("OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
