# Merge philosophy (no CI yet)

Until CI exists, reduce risk via **small diffs** and **explicit proof**.

## Default practice
- Prefer small, reviewable changes.
- Always report verification as **commands + results** (even if manual).

## Proof format (required in outputs)
Include a short proof block:
- what you ran (commands / steps)
- what passed/failed
- what remains unverified (if any)

Example:
- Proof:
  - `python -m pytest -q` ✅ (12 passed)
  - `ruff check .` ✅
  - Manual: opened `/settings`, confirmed toggle persists ✅

## Handling uncertainty
If something cannot be verified locally:
- state the limitation
- propose the least-risk next step to validate
