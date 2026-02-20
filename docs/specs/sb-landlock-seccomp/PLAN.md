# PLAN — sb-landlock-seccomp

1. Capture current `bin/sb` `docker run` construction and insertion point for seccomp mode.
2. Add `security/seccomp-landlock.json` (Docker default profile + minimal Landlock syscall allow).
3. Add `SB_SECCOMP` mode resolver in `bin/sb` and inject matching `--security-opt`.
4. Add concise verification doc with A/B diagnostic and acceptance steps.
5. Run script-level validation (`bash -n`, targeted grep) and capture commands.
