---
name: ui-validation
description: Orchestrates UI validation using a browser automation tool (Playwright via MCP). Decides WHAT to verify, WHEN to run it, and WHAT evidence to capture (screenshots/logs). Does not contain tool/runtime details.
---

# UI Validation Policy (Playwright via MCP)

## Use when
- Any change touches UI/UX, routing, auth, forms, navigation, or CSS/layout.
- You need proof that the UI works (screenshots + short run log).
- You need to reproduce a reported UI bug quickly.

## Do NOT use when
- Pure backend changes with no user-facing impact.
- The task can be verified with unit tests or API checks only.

## Inputs I need (infer if possible; otherwise ask)
- Target URL (prefer dev URL). If multiple candidates exist, list them and ask to choose.
- Critical user flow(s) to validate (default: smoke + one happy path).
- Any auth constraints (use test account or pre-provided session; never ask for real passwords).

## Standard validation checklist (default)
1) **Smoke navigation**
   - Home loads, main routes render, no obvious console errors.
2) **Primary flow (choose 1)**
   - Login → redirect → expected page
   - Create/update entity → success message
   - Checkout/contact form → submit confirmation
3) **Responsive snapshots**
   - Desktop + Mobile (at least 2 viewports)
4) **Broken-link spot check**
   - Validate top-level nav links (not the whole internet)

## Evidence to produce
- 2–6 screenshots saved to a temp location (desktop/mobile + key step).
- Short console log summary:
  - What passed
  - What failed (selector/step + error)
  - Repro steps + URL

## Execution rule
- Use the Playwright MCP tools to execute the steps.
- Prefer robust waits (URL/selector/load-state) over fixed sleeps.
- Keep runs deterministic: avoid randomness, keep timeouts explicit.

## Output format
- Results summary (pass/fail per checklist item)
- Screenshot paths
- Minimal repro steps if something fails