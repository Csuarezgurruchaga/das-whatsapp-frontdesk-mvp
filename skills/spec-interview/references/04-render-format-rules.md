## Step 1 — Render Format Rules (HARD, ALWAYS)

You MUST ALWAYS render interview questions in the following exact **“ronda spec-interview”** format:

### 1) Round header (mandatory)
At the start of each round, print:

- `## Ronda N (Qx–Qy)`

where `N` is the round number and `Qx–Qy` is the inclusive range of questions in this round.

### 2) Per-question header (mandatory)
Each question MUST start with exactly:

- `Q0 — <título>`
- `Q1 — <título>`
- etc.

### 3) Options formatting (mandatory)
Each question MUST include options on separate lines with this exact prefixing:

- `A) ...`
- `B) ...`
- (optional `C) ...`, `D) ...`)
- `E) Other: <texto>`
- `F) Not sure / decide later`

Rules:
- You may include **A–D** as needed (2–4 choices), but **E and F are ALWAYS required**.
- If deferral is truly not acceptable, you MUST still show `F)` but annotate it, e.g.:
  - `F) Not sure / decide later (allowed, but blocks PLAN/TASKS until resolved)`

### 4) Meta-options single-line rule (mandatory)
After the A–F lines, you MUST include meta-options in **one single line** exactly:

- `G) Explain options, H) Compare, I) Recommend, J) Show examples`

### 5) End-of-round answer instruction (mandatory)
At the end of the round, you MUST instruct the user:

- `Respond in ONE single line with comma-separated pairs: Q0=..., Q1=..., ...`

And you MUST clarify the free-text case:

- `For free text: Q0=E: <your-text>`

You MUST also include a short exact example (minimum):

- `Example: Q0=E: voice-agent-mvp, Q1=A`

### Answer format requirement (strict)

At the end of each round, you MUST require answers in **ONE single line**, using comma-separated pairs: `Qn=...`.

**Valid format (case-insensitive):**
- `Q1=A, Q2=D, Q3=C`
- `q1=a, q2=d, q3=c`
- `Q1=E: <text>, Q2=F, Q3=B`

**Hard rules**
- All answers MUST be in **one line** only (no newlines).
- Items MUST be separated by commas `,`
- A space after comma is optional: `Q1=A,Q2=B` is valid.
- Letter choices are **case-insensitive** (A/a are equivalent).
- For `E) Other`, the format MUST be: `Qn=E: <free text>`
- For Meta-options `G/H/I/J` are VALID answers (helper requests) and MUST follow the procedure in THIS DOCUMENT under the heading `## Step 1G — Meta-option handling (mandatory)`.

If the user does not comply, politely ask them to resend using the exact format.

Compliance note: `Qn=G/H/I/J` counts as compliant input (helper mode), not a formatting error.
