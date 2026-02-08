#!/usr/bin/env python3
"""
Generate/overwrite docs/specs/<slug>/CHECKPOINT.md from TASKS Execution status.

Best-effort helper:
- Does NOT invent requirements.
- Only summarizes what it can reliably infer from TASKS.md.

Usage:
  python scripts/checkpoint_from_tasks.py <slug>
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

TASK_RE = re.compile(r"\b(T\d+\.\d+)\b")


def die(msg: str) -> None:
    print(f"CHECKPOINT FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/checkpoint_from_tasks.py <slug>", file=sys.stderr)
        raise SystemExit(2)

    slug = sys.argv[1].strip()
    if not slug:
        die("Missing <slug> argument")

    spec_dir = Path("docs/specs") / slug
    tasks_path = spec_dir / "TASKS.md"
    if not tasks_path.exists():
        die(f"Missing TASKS.md: {tasks_path}")

    text = tasks_path.read_text(encoding="utf-8")

    # Extract execution status block
    parts = re.split(r"(?m)^\s*##\s+Execution status\s*$", text)
    if len(parts) < 2:
        die("TASKS.md missing '## Execution status' section")

    exec_block = parts[-1]
    exec_block = re.split(r"(?m)^\s*##\s+", exec_block)[0]

    # Try to find current task
    m_ct = re.search(r"(?im)^\s*Current task:\s*(.+?)\s*$", exec_block)
    current_task_line = m_ct.group(1).strip() if m_ct else ""
    m_task = TASK_RE.search(current_task_line)
    current_task = m_task.group(1) if m_task else ""

    # Completed tasks from checkboxes
    completed = []
    for m in re.finditer(r"(?im)^\s*-\s*\[x\]\s*(T\d+\.\d+)\b", text):
        tid = m.group(1)
        if tid not in completed:
            completed.append(tid)

    # Fallback: completed tasks list inside execution status
    if not completed and re.search(r"(?im)^\s*Completed tasks:\s*$", exec_block):
        after = re.split(r"(?im)^\s*Completed tasks:\s*$", exec_block, maxsplit=1)[1]
        for line in after.splitlines():
            if not line.strip():
                continue
            if not re.match(r"^\s*[-*]\s+", line) and not line.startswith(" "):
                break
            m = TASK_RE.search(line)
            if m and m.group(1) not in completed:
                completed.append(m.group(1))

    today = date.today().isoformat()

    out = []
    out.append(f"# CHECKPOINT — {slug}")
    out.append("")
    out.append(f"Last updated: {today}")
    out.append("")
    out.append("## Completed")
    if completed:
        for tid in completed[-10:]:
            out.append(f"- {tid}")
    else:
        out.append("- (none recorded)")
    out.append("")
    out.append("## Current / Next")
    out.append(f"- Next task: {current_task or '(not detected)'}")
    out.append("- Status: READY")
    out.append("")
    out.append("## Important constraints")
    out.append("- Follow SPEC/PLAN/TASKS/ACCEPTANCE; implement max 1–2 tasks per run.")
    out.append("")
    out.append("## Gotchas / Risks discovered")
    out.append("- (none recorded)")
    out.append("")
    out.append("## Safe resume instructions")
    out.append("- Re-open TASKS.md → Execution status and continue from Current task.")
    out.append("- Ensure you are on impl/<slug>, then implement 1–2 tasks, commit per task, push per chunk.")

    checkpoint_path = spec_dir / "CHECKPOINT.md"
    checkpoint_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {checkpoint_path}")


if __name__ == "__main__":
    main()
