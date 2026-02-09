# Cloud Run Investigate (READ-ONLY) — Extended Playbook

This document is **reference-only**. It expands the Investigate mode into a practical, repeatable triage loop.
It does **not** override `SKILL.md` guardrails:
- Investigate = **READ-ONLY**
- No mutate commands unless explicitly authorized

---

## Scope

Use this playbook when troubleshooting **Cloud Run services** (not jobs) with symptoms like:
- 5xx / 429 spikes
- timeouts / latency spikes
- cold starts
- auth failures (401/403)
- container startup failures (PORT not listening)
- resource exhaustion (OOM / CPU saturation)

---

## Inputs (preferred)

- `PROJECT_ID`
- `REGION`
- `SERVICE_NAME`
- `INCIDENT_WINDOW` (default: `2h`; examples `30m`, `24h`)
- Optional: `LAST_KNOWN_GOOD_REVISION`, `REQUEST_ID`, example URL/path, known deploy time

If any are missing, do discovery first (see below).

---

## Safety rules (READ-ONLY)

Allowed categories:
- `list`, `describe`, `get-iam-policy`
- `run services logs read`
- `logging read`
- `monitoring time-series list`

Not allowed in Investigate:
- `update`, `create`, `delete`, `deploy`, `set-iam-policy`, `update-traffic`

If mitigation seems necessary: STOP and request explicit authorization with:
- WHY
- EXPECTED_EFFECT
- ROLLBACK_COMMAND

---

## Discovery (when inputs are UNKNOWN)

### 1) Confirm current gcloud context
```bash
gcloud config get-value account
gcloud config get-value project
gcloud config get-value compute/region
```

### 2) List services in region (ask user to pick)
```bash
gcloud run services list --project="$PROJECT_ID" --region="$REGION"
```

---

## Triage loop (ordered, repeatable)

### Step 1 — Snapshot the service (config + status + traffic)
```bash
gcloud run services describe "$SERVICE_NAME"   --project="$PROJECT_ID" --region="$REGION" --format=json
```

Extract at minimum:
- URL (`status.url`)
- traffic splits (`status.traffic`)
- latest created/ready revision names
- runtime service account (`spec.template.spec.serviceAccountName`)
- resources (cpu/memory), concurrency, timeout
- ingress
- VPC connector / egress settings
- env vars / secrets references (names only)

### Step 2 — Revisions overview
```bash
gcloud run revisions list   --project="$PROJECT_ID" --region="$REGION" --service="$SERVICE_NAME"   --format="table(metadata.name,status.conditions[-1].status,status.conditions[-1].message,metadata.creationTimestamp)"
```

Goal:
- identify last-known-good candidate
- detect “new revision just created” vs “traffic unchanged”

### Step 3 — Pull logs quickly (service-level)
Start broad, then narrow.

```bash
gcloud run services logs read "$SERVICE_NAME"   --project="$PROJECT_ID" --region="$REGION" --limit=200
```

Errors only:
```bash
gcloud run services logs read "$SERVICE_NAME"   --project="$PROJECT_ID" --region="$REGION" --limit=200   --filter="severity>=ERROR"
```

If logs are noisy, narrow by revision name (replace `<REV>`):
```bash
gcloud logging read   'resource.type="cloud_run_revision"
   AND resource.labels.service_name="'$SERVICE_NAME'"
   AND resource.labels.revision_name="'<REV>'"
   AND severity>=ERROR'   --project="$PROJECT_ID" --freshness="$INCIDENT_WINDOW" --limit=200 --format=json
```

### Step 4 — Categorize errors (fast clustering)
From logs, cluster by:
- **message fingerprint** (same error text)
- `httpRequest.status` (4xx vs 5xx)
- endpoint/path (if present)
- revision name
- time correlation with deploy

Minimum outputs:
- Top 3 error clusters (count + representative example)
- Whether errors correlate with **newest revision** or all revisions

### Step 5 — Common failure-mode checks (READ-only)

#### A) Container failed to start / PORT issue
Signals:
- messages like “failed to start and listen on the port”
- revision not becoming ready

Check revision readiness:
```bash
gcloud run revisions describe "<REV>"   --project="$PROJECT_ID" --region="$REGION" --format=json
```

#### B) Timeouts / latency spikes
Signals:
- `deadline exceeded`, upstream timeout, request logs show long latency

Pull request logs (if available via Logging):
```bash
gcloud logging read   'resource.type="cloud_run_revision"
   AND resource.labels.service_name="'$SERVICE_NAME'"
   AND httpRequest.requestMethod:*'   --project="$PROJECT_ID" --freshness="$INCIDENT_WINDOW" --limit=200 --format=json
```

#### C) 403 / 401 auth failures
Decide: **Invoker** vs **Runtime SA**

Invoker symptoms:
- 403 at the edge (caller not allowed)

Runtime SA symptoms:
- 403 when calling dependencies (e.g., Storage/Secret Manager/Cloud SQL APIs)

Get runtime SA:
```bash
RUNTIME_SA_EMAIL="$(gcloud run services describe "$SERVICE_NAME"   --project="$PROJECT_ID" --region="$REGION"   --format='value(spec.template.spec.serviceAccountName)')"
echo "$RUNTIME_SA_EMAIL"
```

Roles attached (project-level scan):
```bash
gcloud projects get-iam-policy "$PROJECT_ID"   --flatten="bindings[].members"   --filter="bindings.members:serviceAccount:$RUNTIME_SA_EMAIL"   --format="table(bindings.role)"
```

#### D) OOM / resource saturation
Signals:
- “Killed” / OOM logs
- frequent restarts
- latency increases under load

(If you have Monitoring permissions, collect metrics — see next section.)

---

## Optional — Monitoring metrics (READ-only)

If available, pull a small set of time series for the incident window:
- request count / errors
- latency p95 (if exposed)
- instance count / saturation indicators

Example skeleton (metric types may vary by surface; use as a pattern):
```bash
gcloud monitoring time-series list   --project="$PROJECT_ID"   --filter='resource.type="cloud_run_revision" AND resource.label."service_name"="'$SERVICE_NAME'"'   --interval="endTime=$(date -u +%Y-%m-%dT%H:%M:%SZ),startTime=$(date -u -d "$INCIDENT_WINDOW ago" +%Y-%m-%dT%H:%M:%SZ)"   --limit=10
```

If this fails, keep Investigate purely logs+config and propose enabling Monitoring or confirming IAM.

---

## Decision outputs (what to return)

### Required deliverables
1) **Snapshot summary**: traffic, latest created/ready revision, runtime SA, key perf knobs (cpu/mem/concurrency/timeout)
2) **Top-3 findings** (facts only)
3) **Top-3 hypotheses** (each with evidence and an explicit confidence)
4) **Next best READ command** (exactly 1) and expected outcome
5) **Recommended mitigations** (no write commands in Investigate; only describe what would be done and why)

### “Stop and escalate” criteria
Escalate to Incident mode (request authorization) when:
- sustained 5xx/timeouts impacting users
- new revision clearly caused regression and rollback is the smallest blast radius
- repeated container start failures across revisions

---

## Data to capture for postmortem-lite (Root-cause report)

Even in Investigate, collect these fields so Incident mode can fill the template faster:
- Incident start time (approx) + window
- Trigger (deploy time, traffic shift, dependency outage)
- Affected revision(s)
- Primary error cluster message(s)
- What changed (diff: image/env/secrets/resources/network)
- Hypothesized root cause
- Suggested mitigation and rollback plan
- Validation signals (what confirms recovery)
