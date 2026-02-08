## Step 5 — Generate ACCEPTANCE.md (no code)

### Web app baseline acceptance (mandatory)

If the product includes a web UI (frontend / browser-based app), you MUST include this baseline criterion in ACCEPTANCE.md:

## A0 — Browser smoke (web)
- The app loads in Chromium without critical console errors.
- The primary happy-path flow works end-to-end in the browser.

Notes:
- Keep A0 minimal (smoke only).
- Do NOT add a full E2E test suite unless explicitly required by scope.

Generate acceptance criteria:
- functional acceptance tests (happy path + edge cases)
- non-functional criteria (latency, reliability, cost ceilings if provided)
- observability checks
- security/privacy checks
- rollback criteria

No implementation code.

### Acceptance size guardrail (scope vs quality)

ACCEPTANCE.md should remain small enough to be usable during chunked implementation.

**Soft limit:** aim for 6–10 criteria total.

If ACCEPTANCE.md exceeds **10 criteria**, you MUST do this in order:

1) **Normalize (mandatory):**
   - Merge redundant criteria.
   - Group by category:
     - Functional (happy path)
     - Edge cases / failure modes
     - Non-functional (latency, cost, reliability)
     - Observability
     - Security/Privacy
   - Prefer fewer, stronger criteria over many tiny ones.

2) **Split decision (only if scope indicates it):**
   Propose splitting into 2 specs ONLY if at least one is true:
   - The spec has **> 3 major flows**, OR
   - Criteria naturally split into **2 independent deliverables** (e.g., "core feature" vs "admin/backoffice"), OR
   - There are **multiple integration boundaries** that can ship independently.

If split is triggered:
- Propose Spec A (core value) + Spec B (extensions/hardening/integrations)
- Move acceptance criteria accordingly.
