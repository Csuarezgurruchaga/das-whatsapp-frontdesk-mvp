from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import ipaddress
import os


_VALID_APP_ENVS = {"development", "staging", "production"}
_REQUIRED_ENV_VARS = (
    "DATABASE_URL",
    "SESSION_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
)
_DEFAULT_ATTACHMENTS_DIR = "./storage/attachments"
_DEFAULT_EXPORTS_DIR = "./storage/exports"
_DEFAULT_EXPORTS_TTL_DAYS = 7


@dataclass(frozen=True)
class AllowlistConfig:
    enabled: bool
    networks: tuple[ipaddress._BaseNetwork, ...]


@dataclass(frozen=True)
class ExtrasFeatureFlags:
    attachments_enabled: bool
    exports_enabled: bool
    hard_delete_enabled: bool
    taxonomy_admin_enabled: bool


@dataclass(frozen=True)
class ExtrasConfig:
    attachments_dir: str
    exports_dir: str
    exports_ttl_days: int
    features: ExtrasFeatureFlags


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_app_env() -> str:
    return os.getenv("APP_ENV", "development").lower()


@lru_cache
def get_allowlist_config() -> AllowlistConfig:
    enabled = _is_truthy(os.getenv("WHATSAPP_WEBHOOK_ALLOWLIST_ENABLED"))
    raw = (os.getenv("WHATSAPP_WEBHOOK_ALLOWLIST_CIDRS") or "").strip()
    networks: list[ipaddress._BaseNetwork] = []
    if enabled:
        if not raw:
            raise RuntimeError(
                "WHATSAPP_WEBHOOK_ALLOWLIST_CIDRS is required when "
                "WHATSAPP_WEBHOOK_ALLOWLIST_ENABLED is true"
            )
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            try:
                networks.append(ipaddress.ip_network(entry))
            except ValueError as exc:
                raise RuntimeError(
                    f"Invalid CIDR in WHATSAPP_WEBHOOK_ALLOWLIST_CIDRS: '{entry}'"
                ) from exc
        if not networks:
            raise RuntimeError(
                "WHATSAPP_WEBHOOK_ALLOWLIST_CIDRS must include at least one CIDR"
            )
    return AllowlistConfig(enabled=enabled, networks=tuple(networks))


def _read_non_empty_path(env_name: str, default: str) -> str:
    value = (os.getenv(env_name, default) or "").strip()
    if not value:
        raise RuntimeError(f"{env_name} must not be empty")
    return value


def _read_positive_int(env_name: str, default: int) -> int:
    raw_value = (os.getenv(env_name) or str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} must be a positive integer") from exc
    if parsed <= 0:
        raise RuntimeError(f"{env_name} must be greater than 0")
    return parsed


@lru_cache
def get_extras_config() -> ExtrasConfig:
    return ExtrasConfig(
        attachments_dir=_read_non_empty_path(
            "ATTACHMENTS_DIR", _DEFAULT_ATTACHMENTS_DIR
        ),
        exports_dir=_read_non_empty_path("EXPORTS_DIR", _DEFAULT_EXPORTS_DIR),
        exports_ttl_days=_read_positive_int(
            "EXPORTS_TTL_DAYS", _DEFAULT_EXPORTS_TTL_DAYS
        ),
        features=ExtrasFeatureFlags(
            attachments_enabled=_is_truthy(os.getenv("FEATURE_ATTACHMENTS_ENABLED")),
            exports_enabled=_is_truthy(os.getenv("FEATURE_EXPORTS_ENABLED")),
            hard_delete_enabled=_is_truthy(os.getenv("FEATURE_HARD_DELETE_ENABLED")),
            taxonomy_admin_enabled=_is_truthy(
                os.getenv("FEATURE_TAXONOMY_ADMIN_ENABLED")
            ),
        ),
    )


def validate_runtime_config() -> None:
    env = get_app_env()
    if env not in _VALID_APP_ENVS:
        raise RuntimeError(f"APP_ENV must be one of {sorted(_VALID_APP_ENVS)}")

    if env in {"staging", "production"}:
        missing = [name for name in _REQUIRED_ENV_VARS if not os.getenv(name)]
        if missing:
            missing_list = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {missing_list}")

    get_allowlist_config()
    get_extras_config()
