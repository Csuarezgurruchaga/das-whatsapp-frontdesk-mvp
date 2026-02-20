# TASKS — sb-landlock-seccomp

## T1 — Custom seccomp profile
- Status: Pending
- Deliverable: `security/seccomp-landlock.json` with Landlock syscall allowlist delta only.

## T2 — Runner seccomp modes
- Status: Pending
- Deliverable: `bin/sb` supports `SB_SECCOMP={landlock,default,unconfined}` and logs selected mode.

## T3 — Reproducible verification docs
- Status: Pending
- Deliverable: short docs with A/B diagnosis and acceptance commands.

## T4 — Local verification
- Status: Pending
- Deliverable: `bash -n bin/sb` and targeted grep checks recorded in final report.
