# PLAN — codex-interview-wrapper-arrow-nav

## Overview

Extend the curses batch UI so ↑/↓ moves the pending selection between answer options (wrap-around) and each question starts with A preselected. Preserve the existing horizontal layout, wrap+scroll reader, Enter-to-confirm model, and output format.

## Steps

1) Re-map ↑/↓ from reader scroll to option navigation (wrap-around).
2) Preselect `A` on question entry (fallback to first option present).
3) Keep reader scroll available via PgUp/PgDn/Home/End.
4) Update the on-screen hint and `docs/SB-INTERVIEW.md`.
5) Run `python -m unittest -q` from `tests/`.

