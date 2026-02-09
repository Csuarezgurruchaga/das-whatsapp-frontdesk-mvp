## Cloud Run Incident — Mitigate + Postmortem

**MODE:** Incident (MITIGATE)  
**EXECUTION_MODE:** `<run|propose>`  
**SEVERITY:** `<SEV1|SEV2|SEV3>` (default: `SEV1` if “prod down/users affected”)

**GOAL:** Mitigate first (smallest blast radius), then identify root cause.

**CONTEXT:**
- PROJECT_ID=`<...>`
- REGION=`<...>`
- SERVICE_NAME=`<...>`
- INCIDENT_WINDOW=`<30m|2h>` (default: `2h`)
- LAST_KNOWN_GOOD_REVISION=`<...|UNKNOWN>`
- SYMPTOMS=`<...>` (5xx/latency/timeouts/auth/etc)

**HARD CONSTRAINTS:**
- Writes allowed **only**:
  - `gcloud run services update-traffic ...`
  - `gcloud run services update ...` (only: min/max instances, concurrency, timeout, cpu/memory)
- Each write **MUST** include: **WHY + EXPECTED_EFFECT + ROLLBACK_COMMAND + POST_VALIDATION**.
- If critical info is missing (service/region), do fast discovery and ask me to pick.

**RUNBOOK (mandatory order):**
1) **Snapshot (READ):** service describe + traffic + latestReadyRevision
2) **Confirm impact (READ):** ERROR logs + approximate breakdown by status/revision
3) **Mitigate (WRITE allowlist):**
   - Priority #1: move 100% traffic to last-known-good (if identified)
   - If unknown: route traffic away from newest revision (rollback to previous latestReady)
4) **Immediate post-validation:** logs + smoke check
5) **Stabilization check:** did 5xx/timeouts drop? (based on available evidence)
6) **Root cause:** revision/config diff + targeted logs
7) **Root-cause report:** fill the postmortem-lite template (use `UNKNOWN` where needed)

**OUTPUT:** follow the skill contract + **Root-cause report is mandatory**.
