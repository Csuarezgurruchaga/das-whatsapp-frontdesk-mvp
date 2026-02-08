## Step 1G — Meta-option handling (mandatory)

Meta-options `G/H/I/J` are VALID answers. They are helper requests and DO NOT finalize the decision for the question.

When the user answers `Qn=G/H/I/J`, you MUST:

1) Provide ONLY the requested helper content for that SAME question:
   - G) Explain: briefly define what each A–F option means and when to use it.
   - H) Compare: compare the relevant options using the fixed rubric (Step 1D).
   - I) Recommend: recommend one option, state assumptions, and what would change the recommendation.
   - J) Show examples: provide 2–4 concrete examples for each of A–D.

2) Then immediately re-ask ONLY that SAME question `Qn` using the exact standard format (Q header + A–F lines + meta-options line).

3) Invite either a final decision (A–F) OR another meta-option (G/H/I/J) if they still need help.
Use this exact instruction line:
- `Answer in ONE line: Qn=A/B/C/D/E: <text>/F OR Qn=G/H/I/J`

Hard rules:
- You MUST NOT call `Qn=G/H/I/J` “invalid” or “not valid”.
- If the user answers another meta-option for the same `Qn`, repeat Step 1G for that `Qn` (helper output → re-ask `Qn`) until they choose A–F.
- After a meta-option, do NOT demand answers for other questions—only re-ask `Qn`.
