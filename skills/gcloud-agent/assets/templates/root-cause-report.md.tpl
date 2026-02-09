# Root Cause Report (postmortem-lite) — $INCIDENT_ID

## 1) Executive summary (30–90s)
- **What happened:** $WHAT_HAPPENED
- **Impact:** $IMPACT (who/what was affected, error rates/latency, scope)
- **Duration:** $START_TIME → $END_TIME (timezone: $TZ)
- **Current status:** $STATUS (resolved / mitigated / ongoing)

## 2) Customer / service impact
- **User-visible symptoms:** $SYMPTOMS
- **SLO/SLA impact (if known):** $SLO_IMPACT
- **Blast radius:** $BLAST_RADIUS
- **Estimated affected requests/users:** $AFFECTED

## 3) Timeline (key events)
| Time ($TZ) | Event | Evidence (command/log/link) |
|---|---|---|
| $T0 | Detection | $EVIDENCE0 |
| $T1 | Mitigation action(s) | $EVIDENCE1 |
| $T2 | Recovery confirmed | $EVIDENCE2 |
| $T3 | Root-cause confirmed | $EVIDENCE3 |

## 4) Detection & diagnosis
- **How it was detected:** $DETECTION
- **Primary signals used:** logs / metrics / alerts / user reports
- **Most useful evidence (copy-paste):**
  - $KEY_EVIDENCE_1
  - $KEY_EVIDENCE_2
  - $KEY_EVIDENCE_3

## 5) Root cause (single sentence)
$ROOT_CAUSE

### 5.1 Contributing factors
- $FACTOR_1
- $FACTOR_2
- $FACTOR_3

### 5.2 Why it was not caught earlier
- $WHY_NOT_CAUGHT

## 6) Mitigation / remediation performed
- **Immediate mitigation:** $MITIGATION
- **Changes applied (exact commands):**
```bash
$CHANGES_COMMANDS
```
- **Validation performed (exact commands):**
```bash
$VALIDATION_COMMANDS
```
- **Rollback plan (exact commands):**
```bash
$ROLLBACK_COMMANDS
```

## 7) Follow-ups (action items)
| Priority | Action | Owner | Due | Status |
|---|---|---|---|---|
| P0 | $ACTION_1 | $OWNER_1 | $DUE_1 | $STATUS_1 |
| P1 | $ACTION_2 | $OWNER_2 | $DUE_2 | $STATUS_2 |
| P2 | $ACTION_3 | $OWNER_3 | $DUE_3 | $STATUS_3 |

## 8) Prevent recurrence
- **Guardrails to add:** $GUARDRAILS
- **Monitoring/alerting improvements:** $ALERTING
- **Tests/CI improvements:** $TESTS

## 9) Notes / open questions
- $OPEN_QUESTIONS
