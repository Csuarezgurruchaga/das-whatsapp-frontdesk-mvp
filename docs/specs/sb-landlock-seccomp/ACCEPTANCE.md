# ACCEPTANCE — sb-landlock-seccomp

## Preconditions
- Docker image `codex-sandbox:rg` exists.
- Run from repo root (`~/.codex`) unless specifying absolute paths.

## AC1 — Baseline repro (engine default)
1. Ensure `SB_SECCOMP=default`.
2. Start `sb` and run a command that triggers `exec_command`.
3. Observe failure containing `Sandbox(LandlockRestrict)` and panic at `linux_run_main.rs`.

## AC2 — A/B diagnostic with unconfined
1. Set `SB_SECCOMP=unconfined`.
2. Start `sb` and run the same command.
3. Command executes without Landlock panic.

## AC3 — Final fix with custom seccomp
1. Set `SB_SECCOMP=landlock` (or unset to use default mode).
2. Start `sb` and run the same command.
3. Command executes without panic while seccomp remains active via custom profile.

## AC4 — Runner mode visibility
1. Run `sb` with each mode (`landlock`, `default`, `unconfined`).
2. Confirm logs print selected mode and effective `--security-opt` behavior.
