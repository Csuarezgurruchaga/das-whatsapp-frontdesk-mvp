#!/usr/bin/env python3
"""
Verify the implement-from-spec contract invariants for a given <slug>.

Usage:
  python scripts/verify_contract.py <slug>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ANCHOR_STATEMENT = (
    "The SPEC is the source of truth. If implementation deviates, update the SPEC + TASKS + ACCEPTANCE and record it in the Changelog."
)


def die(msg: str) -> None:
    print(f"CONTRACT FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/verify_contract.py <slug>", file=sys.stderr)
        raise SystemExit(2)

    slug = sys.argv[1].strip()
    if not slug:
        die("Missing <slug> argument")

    spec_dir = Path("docs/specs") / slug
    if not spec_dir.exists():
        die(f"Missing directory: {spec_dir}")

    for fn in ("SPEC.md", "PLAN.md", "TASKS.md", "ACCEPTANCE.md"):
        if not (spec_dir / fn).exists():
            die(f"Missing required file: {spec_dir / fn}")

    spec = read_text(spec_dir / "SPEC.md")

    # Open Questions section must exist and be empty
    m = re.search(r"(?ms)^\s*##\s+Open Questions\s*$\n(.*?)(?=^\s*##\s+|\Z)", spec)
    if not m:
        die("SPEC.md missing '## Open Questions' section")
    open_q = m.group(1).strip()
    if open_q:
        die("SPEC.md Open Questions is not empty")

    # Anchor statement must exist verbatim
    if ANCHOR_STATEMENT not in spec:
        die("SPEC.md missing spec-anchored statement (verbatim)")

    tasks = read_text(spec_dir / "TASKS.md")

    # Execution status must exist
    if not re.search(r"(?m)^\s*##\s+Execution status\s*$", tasks):
        die("TASKS.md missing '## Execution status' section")

    # Execution status must be the last H2 section
    h2s = re.findall(r"(?m)^\s*##\s+(.+?)\s*$", tasks)
    if not h2s or h2s[-1].strip().lower() != "execution status":
        die("'## Execution status' is not the last section in TASKS.md")

    # Execution block must contain required fields
    exec_block = re.split(r"(?m)^\s*##\s+Execution status\s*$", tasks)[-1]
    exec_block = re.split(r"(?m)^\s*##\s+", exec_block)[0]
    for field in ("Status:", "Current task:", "Last updated:"):
        if field not in exec_block:
            die(f"Execution status missing field: {field}")

    print("CONTRACT OK")


if __name__ == "__main__":
    main()
