# Cloud Run Incident (Mitigate + Postmortem) — Launch Prompt (Template)

**MODE:** Incident (MITIGATE)  
**EXECUTION_MODE:** `<run|propose>`  
**SEVERITY:** `<SEV1|SEV2|SEV3>` (default: `SEV1` if “prod down/users affected”)

## Goal
Mitigate first (smallest blast radius), then identify root cause and produce a postmortem-lite root-cause report.

## Context (fill placeholders)
- PROJECT_ID=`${PROJECT_ID:-<PROJECT_ID>}`
- REGION=`${REGION:-<REGION>}`
- SERVICE_NAME=`${SERVICE_NAME:-<SERVICE_NAME>}`
- INCIDENT_WINDOW=`${INCIDENT_WINDOW:-2h}` (examples: `30m`, `2h`)
- LAST_KNOWN_GOOD_REVISION=`${LAST_KNOWN_GOOD_REVISION:-UNKNOWN}`
- SYMPTOMS=`<5xx/latency/timeouts/auth/etc + any concrete examples/snippets>`

## Hard constraints (non-negotiable)
- Writes allowed **only**:
  - `gcloud run services update-traffic ...`
  - `gcloud run services update ...` (only: min/max instances, concurrency, timeout, cpu/memory)
- Each write **MUST** include:
  - **WHY**
  - **EXPECTED_EFFECT**
  - **ROLLBACK_COMMAND**
  - **POST_VALIDATION**
- If critical info is missing (service/region), do fast discovery and ask me to pick.

## Runbook (mandatory order)
1) **Snapshot (READ)**
   - service describe
   - traffic split
   - latestReadyRevision / latestCreatedRevision
2) **Confirm impact (READ)**
   - ERROR logs for the window
   - approximate breakdown by status code and revision (if possible)
3) **Mitigate (WRITE allowlist)**
   - Priority #1: move 100% traffic to last-known-good revision (if identified)
   - If unknown: route traffic away from newest revision (rollback to previous latestReady)
4) **Immediate post-validation**
   - re-check logs
   - run smoke check (service URL) if safe/available
5) **Stabilization check**
   - did 5xx/timeouts drop? (based on evidence available)
6) **Root cause**
   - revision/config diff (image/env/secrets/resources/concurrency/timeouts/vpc/sql)
   - targeted logs for the suspected failure mode
7) **Root-cause report (postmortem-lite)**
   - fill the template `assets/templates/root-cause-report.md.tpl`
   - use `UNKNOWN` where needed

## Output
Follow the skill output contract, and **Root-cause report is mandatory**.
