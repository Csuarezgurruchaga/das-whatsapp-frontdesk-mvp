# Acceptance

## Environment

Primary target is inside the Docker container launched by `sb codex` (workspace mounted at `/workspace`).

## Commands

### 1) Parsing + UI smoke (manual)

1. Start the wrapper:
   - `python3 /workspace/codex-interview-wrapper.py --cmd "codex --no-alt-screen"`
2. In Codex, invoke the `spec-interview` skill.
3. When a round prints (e.g. `Q0 — ...` with `A) ...`, `B) ...`, etc.), verify:
   - A single batch UI appears that shows the full round (all questions).
   - The UI focuses `Q0` first, then advances sequentially after each answer.
   - After answering the last question of the round, the wrapper sends a single line to Codex:
     - `Q0=..., Q1=..., ...`
   - The line is sent automatically and is processed by Codex (no extra Enter needed).

### 2) Meta option behavior (manual)

1. In any question, choose `G` (Explain) / `I` (Recommend) / `J` (Examples).
2. Verify the wrapper continues the wizard through the remaining questions.
3. After the last question of the round, verify the wrapper sends one line that includes all answers + the meta request.
   - Example: `Q0=A, Q1=I, Q2=B`
4. Verify Codex responds and re-asks some questions; wrapper can trigger again on the follow-up prompts.

### 2b) Compare selector (manual)

1. In any question, choose `H` (Compare).
2. Verify a secondary selector appears with:
   - All A–D pair combinations (e.g. `A vs B`, `A vs C`, ...).
   - One option to type custom compare text.
3. Pick a pair and verify the final line includes: `Qn=H: A vs C`.
4. Choose the custom compare option, type text (e.g. `C vs D vs A`), press Enter, and verify the UI returns to the batch flow and continues to the next question.

### 2c) Other (E) inline text (manual)

1. In any question, choose `E` (Other).
2. Verify the UI switches into an inline text entry mode (single-line).
3. Type text, press Enter, and verify the UI continues to the next question (no exit / auto-submit).
4. Repeat `E` on two consecutive questions to ensure Enter events do not "leak" between prompts.

### 3) Prompt fallback (manual)

Run with:
- `python3 /workspace/codex-interview-wrapper.py --no-curses`

Verify it asks for letters via stdin and still sends the single-line answer to Codex.

### 4) Qn-only batch (manual)

Feed a round that includes `Qn — ...` headers without `A)`/`B)` options.
Verify the wrapper prompts for a manual answer per question and still sends a valid answer line.

### 5) Duplicate batch regression (manual)

1. Complete a full round (no meta options).
2. Verify the wrapper does not immediately re-open the same batch after submission.
