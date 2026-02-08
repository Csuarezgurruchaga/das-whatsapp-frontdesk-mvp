# Strict workflow

## Step 0 — Identify the spec slug

If the user did not provide `<slug>`, ask for it.
- Suggest a short kebab-case slug (e.g., `invoice-email-classifier`).

Once `<slug>` is known, set:
- SPEC path = `docs/specs/<slug>/SPEC.md`

If a SPEC file exists, read it first and continue from what is already written.
- Do NOT re-ask answered questions.
- Do NOT overwrite existing decisions without explicit user change.
