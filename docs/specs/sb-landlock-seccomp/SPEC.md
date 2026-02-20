# SPEC — sb-landlock-seccomp

## Objective
Fix sandbox startup failures caused by `LandlockRestrict` without disabling seccomp by default.

## Scope
- Add a custom seccomp profile that keeps Docker default behavior and additionally allows only:
  - `landlock_create_ruleset`
  - `landlock_add_rule`
  - `landlock_restrict_self`
- Integrate seccomp mode selection in `bin/sb` via `SB_SECCOMP`.
- Provide reproducible A/B verification steps in docs.

## Out of Scope
- Host-wide Docker daemon configuration changes.
- Making `seccomp=unconfined` the default mode.
- Broadening syscall allowlist beyond the three Landlock syscalls.

## Functional Requirements
1. `security/seccomp-landlock.json` exists and is based on Docker default seccomp profile with minimal delta.
2. `bin/sb` supports:
   - `SB_SECCOMP=landlock` (default): passes `--security-opt seccomp=<repo>/security/seccomp-landlock.json`.
   - `SB_SECCOMP=default`: uses engine default seccomp (no explicit seccomp opt).
   - `SB_SECCOMP=unconfined`: passes `--security-opt seccomp=unconfined`.
3. `bin/sb` logs active seccomp mode and effective option.
4. Documentation includes before/after validation flow for:
   - baseline failure,
   - `unconfined` diagnostic pass,
   - `landlock` custom-profile pass.

## Non-Functional Requirements
- Preserve current runner behavior except seccomp selection.
- Keep changes minimal and auditable.
- Resolve profile path robustly from script root.

## Open Questions
- None.
