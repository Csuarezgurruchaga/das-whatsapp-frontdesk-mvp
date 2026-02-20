# Sandbox (sb) troubleshooting

## Problem: `Sandbox(LandlockRestrict)` panic before `execve`
Symptom (inside the container):
- `error applying legacy Linux sandbox restrictions: Sandbox(LandlockRestrict)`
- `panic: thread 'main' panicked at linux-sandbox/src/linux_run_main.rs:...`
- exit code `101`

Likely cause:
- Docker default seccomp profile blocking Landlock syscalls (`landlock_*`).

## Seccomp modes (`SB_SECCOMP`)
`sb` supports selecting the seccomp mode via an environment variable:
- `SB_SECCOMP=landlock` (default): uses `security/seccomp-landlock.json`.
- `SB_SECCOMP=default`: uses Docker engine default seccomp profile.
- `SB_SECCOMP=unconfined`: uses `seccomp=unconfined` (debug only).

Invocation note:
- Use `./bin/sb` (or `sb`) to launch Codex UI mode.
- `sb docker` is kept as a legacy alias to the same UI mode.
- `sb` now sets Codex internal sandbox via `SB_CODEX_SANDBOX` (default: `danger-full-access`) to avoid internal Landlock panics. Override if needed:
  - `SB_CODEX_SANDBOX=workspace-write`
  - `SB_CODEX_SANDBOX=read-only`
- `sb` also enables Codex bypass mode by default (`SB_CODEX_BYPASS_SANDBOX=1`), equivalent to `--dangerously-bypass-approvals-and-sandbox`. Set `SB_CODEX_BYPASS_SANDBOX=0` to disable it.

## A/B verification steps
Run from the repo root (`~/.codex`).

1) Baseline repro (engine default)
```bash
export SB_SECCOMP=default
./bin/sb
```
Then run any action that triggers `exec_command` in the sandbox and confirm the Landlock panic.

2) Diagnostic confirm with unconfined
```bash
export SB_SECCOMP=unconfined
./bin/sb
```
Repeat the same action and confirm it no longer panics.

3) Final fix with custom seccomp (Landlock)
```bash
export SB_SECCOMP=landlock
./bin/sb
```
Repeat the same action and confirm it works without `unconfined`.

## Notes on the profile source
`security/seccomp-landlock.json` is vendored from Moby's Docker seccomp default profile (`profiles/seccomp/default.json`).
For Moby `v24.0.6`, the Landlock syscalls are already allowlisted:
- `landlock_create_ruleset`
- `landlock_add_rule`
- `landlock_restrict_self`
