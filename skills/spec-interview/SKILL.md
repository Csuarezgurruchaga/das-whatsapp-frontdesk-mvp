---
name: spec-interview
description: Interview the user to complete a SPEC.md, then generate PLAN.md, TASKS.md and ACCEPTANCE.md. Use multiple-choice questions with built-in explain/compare/recommend helpers. Do not write code until the spec is complete.
metadata:
  short-description: Spec-driven interview → SPEC/PLAN/TASKS/ACCEPTANCE (atomic tasks + size guardrails + spec-anchored)
---

# Purpose

This skill is implemented as a modular, file-based spec. The **authoritative** rules are in `references/`.

When executing this skill, you MUST follow the referenced rules as if they were included inline here.

---

## References index (authoritative)

1) Purpose + Inputs/Outputs  
- references/00-purpose-and-io.md

2) Strict workflow (slug, read existing, do not re-ask)  
- references/01-strict-workflow.md

3) Spec size guardrails + split output rules + session safety  
- references/02-splitting-guardrails.md

4) Interview loop (NO coding), constraints-first ordering, option briefs, unknown term detector, comparison rubric, recommend mode, deferral guardrails  
- references/03-interview-loop.md

5) Render Format Rules (HARD, ALWAYS) + Answer format requirement  
- references/04-render-format-rules.md

6) Meta-option handling (mandatory)  
- references/05-meta-option-handling.md

7) Update SPEC.md continuously + Mandatory SPEC structure + Decision logging + Changelog + spec-anchored contract  
- references/06-spec-update-and-structure.md  
Template: assets/templates/SPEC.template.md

8) Generate PLAN.md (no code)  
- references/07-plan-generation.md  
Template: assets/templates/PLAN.template.md

9) Generate TASKS.md (atomic tasks, mandatory)  
- references/08-tasks-generation.md  
Template: assets/templates/TASKS.template.md

10) Generate ACCEPTANCE.md (no code)  
- references/09-acceptance-generation.md  
Template: assets/templates/ACCEPTANCE.template.md

11) Interview question quality guidelines + Output discipline  
- references/10-question-quality-and-output-discipline.md