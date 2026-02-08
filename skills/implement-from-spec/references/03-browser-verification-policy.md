# Browser verification policy (web apps)

Playwright MAY be used only when required by contract.

## Allowed
Use Playwright ONLY if:
- the current task changes user-facing behavior (UI, routing, auth, forms), AND
- ACCEPTANCE.md or TASKS.md explicitly requires browser-level verification.

If allowed, keep it minimal:
- smoke check (happy path)
- avoid flaky waits
- report exact checks performed and outcome

## Not allowed
If the contract does NOT explicitly require browser verification:
- Do NOT run browser automation.
- Do NOT add Playwright as a dependency.
- Do NOT add E2E tests.
- Limit verification to repo-defined checks (unit tests / lint / build).
