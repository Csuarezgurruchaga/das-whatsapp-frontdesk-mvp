# Multi-agent collaboration safety

## Single-writer policy (hard)
Only the PRIMARY (orchestrator) agent may:
- change branches
- stage/commit/push
- update SPEC/PLAN/TASKS/ACCEPTANCE/CHECKPOINT
- merge or resolve conflicts

## Sub-agent scope policy (hard)
If sub-agents are used:
- each sub-agent works on exactly ONE assigned TaskID
- sub-agents MUST NOT update docs or Git state
- sub-agents MUST NOT edit the same file concurrently

## Integration rule
PRIMARY integrates sequentially: review → verify → commit per task → update docs → push.
