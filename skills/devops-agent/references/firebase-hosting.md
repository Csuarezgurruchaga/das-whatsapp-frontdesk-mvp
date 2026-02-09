# Firebase Hosting Reference (devops-agent)

## When to Use `firebase-tools`
Use `firebase-tools` for Hosting operations:
- Deploying a new release (`deploy --only hosting`)
- Preview channels (`hosting:channel:deploy`)
- Rollback (`hosting:rollback`)
- Multi-site Hosting targets (`.firebaserc`)

## React Router / SPA Gotcha
If you don't configure rewrites to `/index.html`, deep links like `/variant-01` will 404 on refresh.
In `firebase.json`, add:

```json
{
  "hosting": {
    "rewrites": [{ "source": "**", "destination": "/index.html" }]
  }
}
```

## Local vs CI Auth (decision points)
- Local: interactive login is fine.
- CI: avoid long-lived tokens in plaintext if possible. Prefer service-account-based auth if your org policy allows it.

## Minimal Validation Checklist
- `GET /` returns 200
- `GET /variant-01` returns 200 and serves the SPA HTML
- Static assets load (check a CSS/JS asset response is 200)

