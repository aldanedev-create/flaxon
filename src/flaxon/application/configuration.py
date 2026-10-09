from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


def _coerce(value: str) -> Any:
    """
    Coerce a string value to the appropriate Python type.

    Supports:
        - Boolean: true/false, yes/no, on/off
        - Integer: numbers
        - List: comma-separated values
        - String: everything else
    """
    lowered = value.lower()

    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False

    if value.isdigit():
        return int(value)
    if value.startswith("-") and value[1:].isdigit():
        return int(value)

    if "," in value:
        return [item.strip() for item in value.split(",") if item.strip()]

    return value


class Config(dict[str, Any]):
    """
    Configuration container with environment variable support.

    Loads configuration from:
        1. Default values
        2. Dictionary values passed in
        3. Environment variables (prefixed with FLAXON_)
    """

    DEFAULTS: dict[str, Any] = {
        "ENV": "development",
        "DEBUG": False,
        "SECRET_KEY": None,
        "ALLOWED_HOSTS": ["localhost", "127.0.0.1"],
        "MAX_BODY_SIZE": 10 * 1024 * 1024,
        "TRUSTED_PROXIES": [],
        "PROXY_HEADERS": ["x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"],
    }

    def __init__(
        self,
        values: Mapping[str, Any] | None = None,
        *,
        prefix: str = "FLAXON_",
    ) -> None:
        """Initialize configuration."""
        super().__init__(self.DEFAULTS)

        if values:
            self.update(values)

        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):]
                self[config_key] = value if config_key == "SECRET_KEY" else _coerce(value)

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to configuration values."""
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(
                f"Configuration has no attribute '{name}'. "
                f"Available keys: {', '.join(self.keys())}"
            ) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow attribute-style setting of configuration values."""
        self[name] = value

    def get_env(self) -> str:
        """Get the current environment name."""
        return str(self.get("ENV", "development"))

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.get_env() == "development"

    def is_testing(self) -> bool:
        """Check if the environment is testing."""
        return self.get_env() == "testing"

    def is_staging(self) -> bool:
        """Check if the environment is staging."""
        return self.get_env() == "staging"

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.get_env() == "production"

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return bool(self.get("DEBUG", False))

    def get_secret_key(self) -> str | None:
        """Get the secret key."""
        return self.get("SECRET_KEY")

    def get_allowed_hosts(self) -> list[str]:
        """Get the list of allowed hosts."""
        hosts = self.get("ALLOWED_HOSTS", [])
        if isinstance(hosts, str):
            return [host.strip() for host in hosts.split(",")]
        return list(hosts) if hosts else []

    def get_max_body_size(self) -> int:
        """Get the maximum body size in bytes."""
        return int(self.get("MAX_BODY_SIZE", 10 * 1024 * 1024))

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to a plain dictionary."""
        return dict(self)
