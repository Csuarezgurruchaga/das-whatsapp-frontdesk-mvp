# Production Deployment — Debian + Docker Compose

This runbook packages `chatbot-das` for a single Debian host with:

- versioned app image
- `mysql:8` in the same compose stack
- `nginx` terminating TLS
- persistent host directories under `/srv/chatbot-das`

## 1. Host prerequisites

Install on the Debian host:

- Docker Engine
- Docker Compose plugin
- a way to obtain TLS certs for the public domain used by the UI and webhook

Create the runtime directories:

```bash
sudo mkdir -p \
  /srv/chatbot-das/mysql \
  /srv/chatbot-das/attachments \
  /srv/chatbot-das/exports \
  /srv/chatbot-das/certs \
  /srv/chatbot-das/env
```

Recommended ownership baseline:

```bash
sudo chown -R root:root /srv/chatbot-das
sudo chmod 700 /srv/chatbot-das/env
sudo chmod 755 /srv/chatbot-das/mysql /srv/chatbot-das/certs
sudo chown 10001:10001 /srv/chatbot-das/attachments /srv/chatbot-das/exports
sudo chmod 750 /srv/chatbot-das/attachments /srv/chatbot-das/exports
```

The production app image runs as UID/GID `10001`, so `attachments` and `exports` must stay writable for that identity. Re-run `make das-prod-init` after restoring backups or moving data onto the host so existing nested files are normalized recursively for that runtime user.

## 2. Build and publish the app image

Build from the repo root:

```bash
docker build -f Dockerfile.prod -t ghcr.io/csuarezgurruchaga/chatbot-das:2026-04-17-1 .
```

Push the image to the registry you use:

```bash
docker push ghcr.io/csuarezgurruchaga/chatbot-das:2026-04-17-1
```

Use a new immutable tag for every deploy. Do not deploy `latest`.

Current published example from this rollout:

```bash
ghcr.io/csuarezgurruchaga/chatbot-das:2026-04-17-1
```

## 3. Prepare the deployment bundle on the server

Copy these files to the server into one working directory, for example `/opt/chatbot-das`:

- `Makefile`
- `docker-compose.prod.yml`
- `nginx.prod.conf`

Create `/srv/chatbot-das/env/.env.prod` from `.env.prod.example`.

Minimum values to set:

- `APP_IMAGE`
- `MYSQL_IMAGE`
- `NGINX_IMAGE`
- `SESSION_SECRET`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`

`DATABASE_URL` is derived by `docker-compose.prod.yml` from `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD`, so you do not maintain it separately for this embedded-MySQL topology.

Default persistent host paths are already wired to:

- `/srv/chatbot-das/mysql`
- `/srv/chatbot-das/attachments`
- `/srv/chatbot-das/exports`
- `/srv/chatbot-das/certs`

Copy TLS files into:

- `/srv/chatbot-das/certs/fullchain.pem`
- `/srv/chatbot-das/certs/privkey.pem`

## 4. First deploy

From the directory containing `Makefile` + `docker-compose.prod.yml`:

```bash
make das-prod-init
make das-prod-pull
make das-prod-up
```

`make das-prod-up` now applies migrations through a one-off app container before recreating `app`/`nginx`. That path assumes Alembic revisions are backward-compatible with the still-live app while the migration runs.

If a release includes a non-backward-compatible migration, use a maintenance window instead:

```bash
make das-prod-init
make das-prod-pull
make das-prod-up-maintenance
```

Check the stack:

```bash
make das-prod-ps
make das-prod-logs
```

## 5. Smoke checks

Run at least these checks:

```bash
curl -I https://your-domain.example/
curl -I https://your-domain.example/webhooks/whatsapp
```

Then verify:

- login works
- `/realtime/ws` upgrades correctly behind Nginx
- WhatsApp webhook verify works
- invalid webhook signatures are rejected
- attachments and exports are served through `X-Accel-Redirect`

## 6. Restart and power-loss expectations

This deploy keeps state in host paths, not in the app image:

- MySQL data persists in `/srv/chatbot-das/mysql`
- attachments persist in `/srv/chatbot-das/attachments`
- exports persist in `/srv/chatbot-das/exports`

If the host reboots or containers restart, data is preserved as long as those directories are not deleted and the disk remains healthy.

The services use `restart: unless-stopped`, so they should come back automatically after Docker starts again.

## 7. Backup

Database dump:

```bash
docker compose --env-file /srv/chatbot-das/env/.env.prod -f docker-compose.prod.yml exec -T mysql \
  mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" \
  > chatbot-das-$(date +%F-%H%M).sql
```

Filesystem backup targets:

- `/srv/chatbot-das/mysql`
- `/srv/chatbot-das/attachments`
- `/srv/chatbot-das/exports` if you need export retention

Back up the `.env.prod` file via your secret-management process, not in git.

## 8. Rollback

To roll back the app:

1. set `APP_IMAGE` in `.env.prod` to the previous known-good tag
2. pull again
3. recreate the stack

```bash
make das-prod-pull
make das-prod-up
```

If a migration introduced an incompatible schema change, restore the previous DB backup before reopening traffic.

## 9. Operational notes

- Keep `APP_ENV=production` so secure cookies and signature validation stay enabled.
- In the embedded-MySQL topology, `DATABASE_URL` is composed from `MYSQL_*` values by Compose.
- Do not bind mount the repo source code in production.
- Do not store real secrets in repo-tracked files.
- Use `make das-prod-up` only for backward-compatible Alembic revisions. For incompatible schema changes, use `make das-prod-up-maintenance`.
- `make das-prod-logs`, `make das-prod-ps`, and `make das-prod-down` intentionally avoid TLS-file prechecks so they remain usable during certificate incidents and other recovery scenarios.
- The recommended operator entrypoint on Debian is `make das-prod-up`.
