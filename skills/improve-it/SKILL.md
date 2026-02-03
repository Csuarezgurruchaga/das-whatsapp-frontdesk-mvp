---
name: improve-it
description: Repo-first brainstorming that produces high-signal, actionable, prioritized improvements for an existing app (no fluff).
metadata:
  short-description: Brainstorm + prioritize practical app improvements (repo-first)
---

# Purpose

Create a **high-signal improvement backlog** for an already-built app by:
- inspecting the repository to infer stack, architecture, and bottlenecks
- proposing improvements that make sense for this codebase
- prioritizing by impact vs effort
- producing tasks that can be implemented immediately

This skill is a fusion of:
- "brainstorming superpowers" style (many ideas, but still structured)
- "hyperpowers" style (decision + prioritization + execution guidance)
- "marketplace/skills plugin" style (repeatable output templates)

# Inputs (OPTIONAL)

User may provide any of these (none are mandatory):
- goals (e.g., reduce errors, improve conversion, reduce support)
- constraints (time, budget, “no rewrites”, etc.)
- current pain points (bugs, UX confusion, retries, duplicates)
- “do not suggest” list (what to avoid)

If user provides nothing: infer from repo and still produce a useful backlog.

# Mandatory repo inspection (MUST DO)

Before suggesting anything, you MUST examine the repository and extract evidence for:

1) Product surface
- README, docs, routes, UI text, handlers, workflows

2) Tech stack & runtime
- package.json / lockfiles
- requirements.txt / pyproject.toml
- go.mod
- Dockerfile, docker-compose
- env templates, config patterns
- CI/CD: GitHub Actions, pipelines
- deployment hints: cloud run/vercel/k8s/terraform/etc.

3) Architecture
- entrypoints (main/app/server)
- API boundaries (controllers/routers)
- data layer (ORM, migrations)
- background jobs / queues / schedulers
- auth/session patterns
- error handling strategy
- tests (unit/integration/e2e)
- logging + metrics + tracing

4) Operational posture
- secrets management (env, vault, secret manager)
- monitoring & alerting presence
- retry/idempotency patterns
- rate limits / external APIs integration

# Anti-fluff rules (STRICT)

You MUST NOT suggest random improvements.

Every single suggestion MUST include:
- PROBLEM: what is wrong / what users feel / what breaks
- EVIDENCE: repo evidence OR clearly labeled inference
- SOLUTION: what to do (concrete)
- EFFORT: S / M / L
- IMPACT: Low / Med / High
- CONFIDENCE: Low / Med / High
- VERIFICATION: how we know it worked (test/metric/log)

Forbidden suggestions unless justified by repo evidence + clear ROI:
- “add AI”
- “improve UI”
- “add caching”
- “refactor everything”
- “rewrite architecture”
- “add dark mode”
- “switch language/framework”

If repo evidence is missing, you may propose an improvement only if:
- it’s a safe best practice with minimal risk
- you clearly label it as INFERENCE
- you propose a minimal-scoped version

# Output format (MUST FOLLOW)

## 0) Repo Snapshot (evidence-based)
- Detected stack
- Deploy/infra signals
- Subsystems (API/UI/DB/workers)
- Risk posture (tests/logging/secrets)

## 1) Brainstorm Map (divergent thinking, but useful)
Generate 20–40 ideas max, grouped by:
- UX & Product
- Reliability & Correctness
- Performance & Cost
- Security & Privacy
- Observability & Ops
- Developer Experience

Each idea must be 1 line and must not be generic.

## 2) Prioritized Backlog (convergent)
Create a table sorted by ROI:

Columns:
- Title
- Category
- Problem
- Proposed solution
- Effort (S/M/L)
- Impact (Low/Med/High)
- Confidence (Low/Med/High)
- Evidence tag (repo-evidence / inference)
- Verification (how to validate)
- “Why now” (1 line)

Prioritization rule:
- Prefer: High impact + High confidence + Low effort
- Deprioritize: Low confidence + High effort

## 3) Top 7 improvements (deep detail)
For each:
- What to change
- Where (likely files/modules)
- Steps (5–10 bullets)
- Acceptance criteria (pass/fail)
- Risks & mitigations
- Quick test plan

## 4) Quick Wins (<= 2 hours)
List 5–10 items that can ship today.

## 5) “One thing only”
Pick the single best ROI improvement and explain:
- why it beats the others
- what metric/log confirms success

## 6) Optional deliverables (only if user asks)
- GitHub Issues ready-to-paste
- PR description template
- commit message suggestions

# Small Q&A policy

If user didn’t provide goals/constraints and it materially affects prioritization:
Ask up to 3 short questions, then proceed anyway.

Example questions:
1) What is your #1 goal? (reduce errors / faster / better UX / lower cost)
2) Any hard constraints? (no rewrites / 1 week / no extra services)
3) Where is most pain? (onboarding / payments / search / latency / support)

# Quality bar

You must behave like a pragmatic senior engineer:
- prefer incremental improvements
- preserve existing architecture unless clearly harmful
- use safety-first changes (correctness > reliability > observability > perf > UX polish)
- keep outputs implementation-ready

