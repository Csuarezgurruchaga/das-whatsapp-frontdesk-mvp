## Step 1 — Interview loop (NO coding)

### Objective

Ask high-signal, non-obvious questions until **Open Questions** becomes empty and all critical decisions are made (or explicitly deferred with documented consequences).

### Interview structure rules

- Ask **2–10 questions per round** (default 6–10; early rounds may be shorter, e.g., Q0–Q1).
- Prefer **multiple-choice (A/B/C/D)** and ALWAYS include as mandatory:
  - `E) Other: <free text>`
  - `F) Not sure / decide later` (ONLY if truly acceptable to defer)

## Step 1A — Constraints-first ordering (reduce confusion)

In the first round(s), prioritize constraints before proposing “stack” choices. Ask about:
- scale/throughput, latency, availability/SLA
- budget/cost sensitivity
- hosting/runtime constraints (Cloud Run? K8s? serverless?)
- data sensitivity/security/privacy/compliance needs
- integration boundaries (existing DB, APIs, auth)
- idempotency/duplication tolerance
- observability requirements

---

## Step 1B — Option briefs (mandatory)

When you provide A–D technical options, each option MUST include a brief:

**Format per option:**
- **What it is (1 line)**
- **When to use (1 line)**

---

## Step 1C — Unknown term detector (mandatory)

If any option includes a term/technology/concept that has NOT appeared in the spec yet (or is niche), you MUST do one of:
- Automatically include a 1–2 line definition inline, OR
- Encourage `G) Explain options`

Additionally, maintain a short **Glossary** section in SPEC.md for new terms introduced.

---

## Step 1D — Comparison rubric (fixed, consistent)

When the user asks `H) Compare`, you MUST use the same rubric every time:

1) Operational complexity  
2) Reliability semantics (retries, DLQ, backoff)  
3) Idempotency & dedupe story  
4) Latency characteristics  
5) Cost drivers  
6) Observability (logs/metrics/tracing)  
7) Vendor lock-in / portability  
8) Edge-case risk (timeouts, concurrency, ordering)

End with:
- “If your #1 priority is X → choose …”
- “If your #1 priority is Y → choose …”
- Any “unknowns” that would change the recommendation

---

## Step 1E — Recommend mode requirements

If the user asks `I) Recommend`, you MUST:
- state the recommendation
- state assumptions (explicitly)
- list missing info (what would change the choice)
- propose 1–2 follow-up questions (but do NOT exceed the 6–10 questions per round overall)

---

## Step 1F — Deferral guardrails (“F) decide later”)

Deferral is allowed, but must be managed:

- If the user picks `F` for a critical decision, you MUST:
  - add it to **Open Questions** with a specific label,
  - describe the consequence of deferring (what in PLAN is blocked or becomes more expensive),
  - add a “Default if not decided” fallback (only if safe), clearly marked as provisional.
