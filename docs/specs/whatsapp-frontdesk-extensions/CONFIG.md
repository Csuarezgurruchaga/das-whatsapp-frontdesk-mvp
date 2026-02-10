# CONFIG — whatsapp-frontdesk-extensions

## Environment variables
- `ATTACHMENTS_DIR` (default: `./storage/attachments`)
  - Base directory for attachment binaries.
  - Later tasks assume relpaths persisted in DB are relative to this root.
- `EXPORTS_DIR` (default: `./storage/exports`)
  - Base directory for on-demand ZIP exports.
- `EXPORTS_TTL_DAYS` (default: `7`)
  - Retention window for generated exports before cleanup.

## Feature flags
- `FEATURE_ATTACHMENTS_ENABLED` (default: `false`)
  - Gates attachments upload/send/history UI and backend endpoints.
- `FEATURE_EXPORTS_ENABLED` (default: `false`)
  - Gates export generation and export download authorization paths.
- `FEATURE_HARD_DELETE_ENABLED` (default: `false`)
  - Gates hard delete action in conversation details.
- `FEATURE_TAXONOMY_ADMIN_ENABLED` (default: `false`)
  - Gates taxonomy admin UI and related endpoints.

## Role matrix (Core representation vs Extras target)
- Current Core roles in code/DB: `agent`, `admin`.
- Extras target roles: `operator`, `admin`, `supervisor`.
- Mapping used for implementation:
  - `operator` maps to current `agent` role in Core.
  - `admin` remains `admin`.
  - `supervisor` is a new role to introduce in Extras role/task work (read-only taxonomy + export permissions).

## Capability matrix (target behavior)
- Attachments (upload/send/view own authorized conversations): `operator`, `admin`.
- Export ZIP request/download: `admin`, `supervisor`.
- Taxonomy admin CRUD (create/edit/rename/archive): `admin`.
- Taxonomy admin read-only: `supervisor`.
- Hard delete conversation artifacts: `admin` only.

## Notes
- Defaults are intentionally local-friendly and on-prem compatible (local path in dev, NAS mount in production).
- Flags default to disabled so rollout can be gradual by environment.
- Referenced by tasks: `T1.1`, `T1.3`, `T1.5`, `T1.6`, `T1.7`, `T2.1`, `T2.2`, `T2.3`, `T4.1`.
