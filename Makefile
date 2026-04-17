APP_ENV_FILE ?= /srv/chatbot-das/env/.env.prod
COMPOSE_FILE ?= docker-compose.prod.yml
RUNTIME_ROOT ?= /srv/chatbot-das
MYSQL_DATA_DIR ?= $(RUNTIME_ROOT)/mysql
ATTACHMENTS_HOST_DIR ?= $(RUNTIME_ROOT)/attachments
EXPORTS_HOST_DIR ?= $(RUNTIME_ROOT)/exports
TLS_CERTS_DIR ?= $(RUNTIME_ROOT)/certs
APP_RUNTIME_UID ?= 10001
APP_RUNTIME_GID ?= 10001

DOCKER_COMPOSE = \
	APP_ENV_FILE=$(APP_ENV_FILE) \
	MYSQL_DATA_DIR=$(MYSQL_DATA_DIR) \
	ATTACHMENTS_HOST_DIR=$(ATTACHMENTS_HOST_DIR) \
	EXPORTS_HOST_DIR=$(EXPORTS_HOST_DIR) \
	TLS_CERTS_DIR=$(TLS_CERTS_DIR) \
	docker compose --env-file $(APP_ENV_FILE) -f $(COMPOSE_FILE)

.PHONY: \
	das-prod-help \
	das-prod-init \
	das-prod-stack-check \
	das-prod-check \
	das-prod-pull \
	das-prod-up \
	das-prod-up-maintenance \
	das-prod-migrate \
	das-prod-ps \
	das-prod-logs \
	das-prod-restart \
	das-prod-down

das-prod-help:
	@printf '%s\n' \
	'Targets disponibles:' \
	'  make das-prod-init     # crea directorios persistentes del host' \
	'  make das-prod-stack-check # valida env + compose sin requerir TLS' \
	'  make das-prod-check    # valida env, compose y certificados' \
	'  make das-prod-pull     # hace pull de las imagenes definidas' \
	'  make das-prod-up       # migra primero y luego recrea app + nginx; requiere migraciones backward-compatible' \
	'  make das-prod-up-maintenance # deploy con ventana de mantenimiento para migraciones incompatibles' \
	'  make das-prod-migrate  # corre alembic upgrade head en un contenedor efimero' \
	'  make das-prod-ps       # muestra el estado del stack' \
	'  make das-prod-logs     # muestra logs recientes de app/nginx/mysql' \
	'  make das-prod-restart  # recrea app + nginx con la misma secuencia segura de migracion' \
	'  make das-prod-down     # baja el stack sin borrar datos' \
	'' \
	'Variables sobreescribibles:' \
	'  APP_ENV_FILE=$(APP_ENV_FILE)' \
	'  COMPOSE_FILE=$(COMPOSE_FILE)' \
	'  RUNTIME_ROOT=$(RUNTIME_ROOT)'

das-prod-init:
	@set -eu; \
	install -d -m 755 "$(MYSQL_DATA_DIR)" "$(ATTACHMENTS_HOST_DIR)" "$(EXPORTS_HOST_DIR)" "$(TLS_CERTS_DIR)"; \
	install -d -m 700 "$(dir $(APP_ENV_FILE))"; \
	chown -R "$(APP_RUNTIME_UID):$(APP_RUNTIME_GID)" "$(ATTACHMENTS_HOST_DIR)" "$(EXPORTS_HOST_DIR)"; \
	chmod 750 "$(ATTACHMENTS_HOST_DIR)" "$(EXPORTS_HOST_DIR)"; \
	printf 'runtime_root=%s\n' "$(RUNTIME_ROOT)"; \
	printf 'env_dir=%s\n' "$(dir $(APP_ENV_FILE))"

das-prod-stack-check:
	@set -eu; \
	test -f "$(APP_ENV_FILE)" || { echo "Missing env file: $(APP_ENV_FILE)" >&2; exit 1; }; \
	test -f "$(COMPOSE_FILE)" || { echo "Missing compose file: $(COMPOSE_FILE)" >&2; exit 1; }; \
	$(DOCKER_COMPOSE) config >/dev/null; \
	echo "prod_stack_check_ok"

das-prod-check: das-prod-stack-check
	@set -eu; \
	test -f nginx.prod.conf || { echo "Missing nginx.prod.conf in current directory" >&2; exit 1; }; \
	test -f "$(TLS_CERTS_DIR)/fullchain.pem" || { echo "Missing TLS cert: $(TLS_CERTS_DIR)/fullchain.pem" >&2; exit 1; }; \
	test -f "$(TLS_CERTS_DIR)/privkey.pem" || { echo "Missing TLS key: $(TLS_CERTS_DIR)/privkey.pem" >&2; exit 1; }; \
	echo "prod_check_ok"

das-prod-pull: das-prod-stack-check
	$(DOCKER_COMPOSE) pull

das-prod-up: das-prod-check
	$(DOCKER_COMPOSE) up -d mysql
	$(MAKE) das-prod-migrate
	$(DOCKER_COMPOSE) up -d app nginx
	$(MAKE) das-prod-ps

das-prod-up-maintenance: das-prod-check
	$(DOCKER_COMPOSE) up -d mysql
	$(DOCKER_COMPOSE) stop app nginx || true
	$(MAKE) das-prod-migrate
	$(DOCKER_COMPOSE) up -d app nginx
	$(MAKE) das-prod-ps

das-prod-migrate: das-prod-stack-check
	$(DOCKER_COMPOSE) up -d mysql
	$(DOCKER_COMPOSE) run --rm --no-deps app alembic upgrade head

das-prod-ps: das-prod-stack-check
	$(DOCKER_COMPOSE) ps

das-prod-logs: das-prod-stack-check
	$(DOCKER_COMPOSE) logs --tail=200 app nginx mysql

das-prod-restart: das-prod-check
	$(DOCKER_COMPOSE) up -d mysql
	$(MAKE) das-prod-migrate
	$(DOCKER_COMPOSE) up -d --force-recreate app nginx
	$(MAKE) das-prod-ps

das-prod-down: das-prod-stack-check
	$(DOCKER_COMPOSE) down
