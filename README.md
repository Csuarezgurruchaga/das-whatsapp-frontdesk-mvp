# chatbot-das

FrontDesk + chatbot de WhatsApp para DAS.

El proyecto cubre:

- chatbot rule-based por YAML
- handoff humano con estados `CHATBOT -> EN_ESPERA -> ASIGNADO -> CERRADO`
- UI operativa de FrontDesk
- auditoría mínima (`conversation_events`, `message_receipts`)
- despliegue on-prem en Debian con Docker Compose

## Source of truth

La especificación activa está en:

- `docs/specs/whatsapp-frontdesk-mvp/SPEC.md`
- `docs/specs/whatsapp-frontdesk-mvp/TASKS.md`
- `docs/specs/whatsapp-frontdesk-mvp/ACCEPTANCE.md`
- `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md`

Notas operativas y memoria del repo:

- `AGENTS.md`

## Modos de entorno

### 1. Desarrollo local

Usa:

- `docker-compose.local.yml`
- `Dockerfile.local`
- `.env.staging.local.example` como plantilla

Características:

- bind mount del código
- MySQL 8 local
- Nginx local en `:8080`
- sirve para iterar y validar UI/backend rápido

### 2. Local prod-like

Mismo stack local, pero con:

- `APP_ENV=staging`
- credenciales reales de WhatsApp
- `ngrok`
- webhook firmado
- eventual cutover temporal del dispatcher si se necesita inbound real end-to-end

Esto se usa sólo para aceptación controlada. No es el modo seguro por defecto.

### 3. Producción Debian

Usa el bundle nuevo:

- `Makefile`
- `Dockerfile.prod`
- `docker-compose.prod.yml`
- `nginx.prod.conf`
- `.env.prod.example`
- `DEPLOYMENT_PROD.md`

Características:

- imagen inmutable
- sin bind mount del repo
- MySQL 8 embebido en Compose
- persistencia en `/srv/chatbot-das/*`
- app corriendo como usuario no root (`uid/gid 10001`)
- entrypoint operativo recomendado: `make das-prod-up`
- si una release trae una migración no backward-compatible, usar `make das-prod-up-maintenance`
- imagen publicada actual para el bundle Debian: `ghcr.io/csuarezgurruchaga/chatbot-das:2026-04-17-1`

## Cómo correr local

1. Crear `.env.staging.local` desde `.env.staging.local.example`
2. Levantar el stack:

```bash
docker compose -f docker-compose.local.yml up --build
```

3. Migrar:

```bash
docker compose -f docker-compose.local.yml exec app alembic upgrade head
```

4. Abrir:

- UI: `http://127.0.0.1:8080/`
- app: `http://127.0.0.1:8000/`

## Variables importantes

Siempre relevantes:

- `APP_ENV`
- `DATABASE_URL`
- `SESSION_SECRET`
- `BOT_MENU_YAML_PATH`

Para WhatsApp real:

- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`

Para storage/extras:

- `ATTACHMENTS_DIR`
- `EXPORTS_DIR`
- `EXPORTS_TTL_DAYS`

Para el bundle Debian:

- `APP_IMAGE`
- `MYSQL_IMAGE`
- `NGINX_IMAGE`

## Lo que otra sesión de Codex debe saber

- El repo activo es este `chatbot-das`, branch operativa `dev`.
- El deploy oficial para Debian ya no es `docker-compose.local.yml`; es `docker-compose.prod.yml`.
- `docker-compose.local.yml` sigue siendo la ruta oficial de desarrollo.
- No usar credenciales reales de WhatsApp en local salvo para una validación prod-like controlada.
- Si se prueba inbound real con una WABA productiva, el dispatcher debe respaldarse y restaurarse exactamente.
- Para aceptación funcional, la checklist está en `docs/specs/whatsapp-frontdesk-mvp/DEPLOYMENT.md`.
- Para deploy de servidor, el runbook correcto es `DEPLOYMENT_PROD.md`.
- En Debian, la forma recomendada de levantar el stack es `make das-prod-up`.
- `make das-prod-up` asume migraciones Alembic backward-compatible; para cambios incompatibles existe `make das-prod-up-maintenance`.
- En el bundle Debian, `DATABASE_URL` no se edita a mano: se deriva desde `MYSQL_DATABASE`, `MYSQL_USER` y `MYSQL_PASSWORD`.
- `make das-prod-logs`, `make das-prod-ps` y `make das-prod-down` siguen disponibles aunque falten certificados, para no bloquear recovery básico.
