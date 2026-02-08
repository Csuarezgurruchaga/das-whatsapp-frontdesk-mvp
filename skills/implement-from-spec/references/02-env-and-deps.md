# Environment & dependency management

Goal: keep installs isolated and reproducible. Never install globally.

## Python (mandatory if task uses Python)
- Use project-local `.venv/` only.
- If `.venv/` does not exist: create it.
- Always upgrade pip inside venv before installs:
  - `python -m pip install --upgrade pip`

### Dependency file policy
- If `requirements.txt` or `requirements-dev.txt` exists: install from it.
- If none exists and project is being bootstrapped: create minimal `requirements.txt` (may be empty).

Hard stops:
- If the task requires Python dependencies but there is no dependency file AND the contract does not allow creating one: STOP.
- Do not guess versions unless SPEC/TASKS defines them.

## Frontend JS/TS (mandatory if task uses frontend tooling)
- Use repo-defined package manager based on lockfile:
  - `package-lock.json` → npm
  - `yarn.lock` → yarn
  - `pnpm-lock.yaml` → pnpm
- Do NOT mix package managers.
- Do NOT delete lockfiles unless TASKS explicitly requires it.
- Commit lockfile changes if dependencies change.

Hard stops:
- If multiple lockfiles exist and TASKS/SPEC does not specify how to resolve: STOP (do not “clean up”).
- If the task would require switching package managers without explicit contract approval: STOP.

## Session resumption
- Reuse existing `.venv/`.
- Keep using the existing lockfile workflow.
