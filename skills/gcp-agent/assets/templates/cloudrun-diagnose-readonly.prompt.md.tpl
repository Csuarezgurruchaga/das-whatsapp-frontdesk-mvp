# Cloud Run Diagnose (Read-Only) — Launch Prompt (Template)

**MODE:** Investigate (READ-ONLY)  
**EXECUTION_MODE:** `<run|propose>` (default: `run` if `gcloud` is authenticated)

## Goal
Diagnose a Cloud Run issue using evidence (service config + revisions/traffic + logs), then propose the minimum safe next steps.

## Context (fill placeholders)
- PROJECT_ID=`${PROJECT_ID:-<PROJECT_ID>}`
- REGION=`${REGION:-<REGION>}`
- SERVICE_NAME=`${SERVICE_NAME:-<SERVICE_NAME>}`
- INCIDENT_WINDOW=`${INCIDENT_WINDOW:-2h}`  (examples: `30m`, `2h`, `24h`)
- SYMPTOMS=`<timeouts/5xx/latency/auth/cold-start/oom + examples/snippets if available>`

## Hard constraints (non-negotiable)
- **MUST NOT** run *or propose* any mutate commands with verbs: `create|update|delete|deploy|set-iam-policy|update-traffic`.
- If mitigation seems necessary, **STOP** and request explicit authorization including:
  - **WHY**
  - **EXPECTED_EFFECT**
  - **ROLLBACK_COMMAND**

## Discovery (only if required fields are UNKNOWN)
1) Verify context:
   - `gcloud config get-value project`
   - `gcloud config get-value compute/region`
2) If SERVICE_NAME is UNKNOWN:
   - list Cloud Run services in the region and ask me to pick one.

## Output (fixed order)
1) **Context Summary** (explicitly mark what was inferred vs provided)
2) **Variables Block** (`.gcp-env`)
3) **Evidence**
   - service+traffic snapshot
   - relevant revisions (latest created/ready + any suspicious revision)
   - ERROR logs for the window
4) **Findings** (≤10 bullets)
5) **Top-3 Hypotheses** (each backed by evidence)
6) **Next best command** (exactly 1 READ command that maximizes information) + what you expect to see
7) **Proposed safe fixes** (recommendations only; no write commands)
8) **Validation plan** (read-only)
