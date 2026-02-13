# Verification & safety (GLOBAL)

## Tests / linters
- If tests/linters exist: run them and report results.
- If they do not exist: state that clearly.
- Do **not** introduce new tooling or test frameworks unless explicitly asked.

## Bugfix protocol (default): no fix without repro
Rule: **no fix without repro**.

When a bug is reported:
1) Create a minimal reproduction that fails (prefer: automated test).
2) Commit the failing repro/test before attempting fixes (use squash/fixup locally so final history is green-only).
3) Implement the fix.
4) Prove the fix by making the repro/test pass and running the relevant suite.
5) Add regression coverage to prevent recurrence.

Acceptable proofs (in order):
- Deterministic automated test (unit/integration/e2e)
- Deterministic repro script/fixture + CI command (if any)
- Logged assertion/invariant + controlled repro steps + captured artifacts

Exceptions (must be stated explicitly in the PR/commit message or change log):
- repro requires external systems not available locally
- non-deterministic/concurrency issues where a stable test is not feasible
- emergency hotfix (must be followed by a repro within N days)

## Command safety
- If a command can modify/delete files or resources: ask first.
- Prefer read-only inspection before mutation.
