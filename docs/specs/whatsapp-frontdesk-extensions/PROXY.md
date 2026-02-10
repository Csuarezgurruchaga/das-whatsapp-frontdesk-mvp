# Reverse-Proxy Download Authorization (T2.1)

This document defines the proxy requirements for attachment/export downloads after backend authorization.

## Backend authorization endpoints

- `GET /conversations/{conversation_id}/attachments/{attachment_id}/download`
- `GET /conversations/{conversation_id}/attachments/{attachment_id}/view`
- `GET /conversations/{conversation_id}/exports/{export_id}/download`

All endpoints require the normal app session cookie and run app-level authorization before returning proxy headers.

## Response headers emitted by backend

- `X-Accel-Redirect: /_internal/attachments/<storage_relpath>` for attachment endpoints
- `X-Accel-Redirect: /_internal/exports/<storage_relpath>` for export downloads
- `Content-Type` set from attachment/export type
- `Content-Disposition`:
  - `inline` for `/view` on viewable attachment MIME types
  - `attachment` for `/download`

The backend does not stream file bytes.

## Nginx reference config (supported path)

```nginx
# App upstream (FastAPI)
location / {
    proxy_pass http://app_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Internal attachment files (NAS/read-only mount)
location /_internal/attachments/ {
    internal;
    alias /mnt/nas/frontdesk/attachments/;
}

# Internal export files (NAS/read-only mount)
location /_internal/exports/ {
    internal;
    alias /mnt/nas/frontdesk/exports/;
}
```

Notes:
- `alias` roots must map to the same storage roots as app `ATTACHMENTS_DIR` and `EXPORTS_DIR`.
- Keep mounts read-only on the proxy host.

## Apache note

- Current backend contract is `X-Accel-Redirect` (Nginx internal redirect).
- For Apache deployments, use an equivalent internal-send mechanism (for example `mod_xsendfile`) with a backend header adapter, or deploy Nginx in front of Apache for protected file serving.
