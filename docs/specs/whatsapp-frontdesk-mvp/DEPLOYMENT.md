# DEPLOYMENT — WhatsApp FrontDesk Core MVP

## Reverse proxy requirements
- Terminate TLS at the reverse proxy and forward traffic to the app over HTTP.
- Forward the original request headers:
  - `X-Forwarded-Proto`, `X-Forwarded-For`, `X-Forwarded-Host` (and optionally `X-Forwarded-Port`).
- Preserve the Host header for URL construction and callbacks.
- Support WebSocket upgrades on `/realtime/ws` (set `Upgrade` + `Connection` headers).
- Route `/webhooks/whatsapp` and `/` to the app service.

## Optional webhook allowlist (recommended at proxy)
- Allowlist should be enforced at the reverse proxy when required by ops/security.
- The app also supports an optional allowlist hook (disabled by default):
  - `WHATSAPP_WEBHOOK_ALLOWLIST_ENABLED` = `true` to enable.
  - `WHATSAPP_WEBHOOK_ALLOWLIST_CIDRS` = comma-separated CIDRs (e.g. `203.0.113.0/24,198.51.100.4/32`).
- When enabled, the app reads the left-most IP from `X-Forwarded-For` (or falls back to the direct client IP).
- Ensure the proxy strips any client-supplied `X-Forwarded-For` and sets its own value.

## Session cookie settings
- `APP_ENV=development` → cookies are not `Secure` (local HTTP is allowed).
- `APP_ENV=staging|production` → cookies are `Secure`, `HttpOnly`, `SameSite=Lax` (requires TLS).
- Keep `SESSION_SECRET` set in all non-dev environments.

## Config validation
- On startup, in `staging`/`production`, the app validates required env vars:
  - `DATABASE_URL`, `SESSION_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`,
    `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`.
- If allowlist is enabled, CIDRs are validated at startup; invalid or empty values fail fast.
