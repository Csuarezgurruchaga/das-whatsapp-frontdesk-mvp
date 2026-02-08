# TASK progress accounting

On every run, compute and report:

- Total tasks = count of all unique TaskIDs (`T<number>.<number>`) present in the backlog.
- Completed tasks = count of tasks marked done via either:
  A) checklist format `- [x] T?.? ...`
  OR
  B) a `Completed tasks:` list inside `## Execution status` (if present)

Report as:
- `TASKS progress: <done>/<total>`
- `Current task: <TaskID>`
- `Remaining: <total-done>`
