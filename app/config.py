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


@dataclass(frozen=True)
class AllowlistConfig:
    enabled: bool
    networks: tuple[ipaddress._BaseNetwork, ...]


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
