"""Typed project settings shared by the server and management commands."""

from __future__ import annotations

import importlib
import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flaxon._imports import import_attribute

management_mode: ContextVar[bool] = ContextVar("flaxon_management_mode", default=False)


class Environment:
    """Read environment values; explicit environment variables override .env."""

    def load(self, path: str | Path) -> None:
        """Load the requested resource using the configured source."""
        load_dotenv = import_attribute("dotenv", "load_dotenv")

        load_dotenv(path, override=False)

    def str(self, name: str, default: Any = None) -> Any:
        """Perform the str operation for environment."""
        return os.environ.get(name, default)

    def bool(self, name: str, default: bool = False) -> bool:
        """Perform the bool operation for environment."""
        value = os.environ.get(name)
        if value is None:
            return default
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"{name} must be a boolean (true/false or 1/0)")

    def list(self, name: str, default: list[str] | None = None) -> list[str]:
        """Return the matching entries."""
        value = os.environ.get(name)
        return (
            list(default or [])
            if value is None
            else [part.strip() for part in value.split(",") if part.strip()]
        )


env = Environment()


class Settings:
    """Validated project configuration. Importing settings never connects to a DB."""

    def __init__(self, source: str | Any = "settings") -> None:
        module = importlib.import_module(source) if isinstance(source, str) else source
        self.root = Path(
            getattr(module, "BASE_DIR", getattr(module, "ROOT", Path(module.__file__).parent))
        ).resolve()
        self.values = {key: getattr(module, key) for key in dir(module) if key.isupper()}
        self.values.setdefault("DEBUG", False)
        self.values.setdefault("JSON_SERIALIZER", "modern")
        self.values.setdefault("PROJECT_NAME", self.root.name)
        self.values.setdefault("TIME_ZONE", "UTC")
        self.values.setdefault("DATABASE_URL", f"sqlite://{self.root / 'data/app.sqlite3'}")
        self.values.setdefault("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
        self.values.setdefault("CSRF_TRUSTED_ORIGINS", [])
        self.values.setdefault("ADMIN_ENABLED", True)
        self.values.setdefault("CMS_ENABLED", True)
        self.values.setdefault("ADMIN_SERVICES_ENABLED", False)
        self.values.setdefault("ADMIN_STORE_BACKEND", "sqlite")
        self.values.setdefault("ADMIN_STORAGE_PATH", self.root / "data/admin.sqlite3")
        self.validate()

    def __getattr__(self, key: str) -> Any:
        try:
            return self.values[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def validate(self) -> None:
        """Check the supplied value against the configured constraints."""
        if self.JSON_SERIALIZER not in {"modern", "legacy"}:
            raise ValueError("JSON_SERIALIZER must be modern or legacy")
        if self.ADMIN_STORE_BACKEND not in {"sqlite", "orm"}:
            raise ValueError("ADMIN_STORE_BACKEND must be sqlite or orm")
        if type(self.DEBUG) is not bool:
            raise ValueError("DEBUG must be a bool; use env.bool()")
        if not isinstance(self.ALLOWED_HOSTS, (list, tuple)) or not self.ALLOWED_HOSTS:
            raise ValueError("ALLOWED_HOSTS must be a non-empty list")
        if not isinstance(self.CSRF_TRUSTED_ORIGINS, (list, tuple)):
            raise ValueError("CSRF_TRUSTED_ORIGINS must be a list")
        for origin in self.CSRF_TRUSTED_ORIGINS:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CSRF_TRUSTED_ORIGINS must contain complete origins without paths")
        ZoneInfo(self.TIME_ZONE)
        if not self.DEBUG:
            self._validate_debug()

    def _validate_debug(self):
        """Apply debug changes for validate."""
        secret = self.values.get("SECRET_KEY")
        if not isinstance(secret, str) or len(secret) < 32:
            raise ValueError(
                "Set FLAXON_SECRET_KEY to a persistent secret of at least 32 characters in production"
            )
        if "*" in self.ALLOWED_HOSTS:
            raise ValueError("Use explicit ALLOWED_HOSTS in production")

    def prepare_database_directory(self) -> None:
        """Perform the prepare database directory operation for settings."""
        url = str(self.DATABASE_URL)
        if url.startswith("sqlite://") and url != "sqlite://:memory:":
            path = Path(url.removeprefix("sqlite://"))
            if not path.is_absolute():
                raise ValueError("Use an absolute SQLite path based on BASE_DIR")
            path.parent.mkdir(parents=True, exist_ok=True)
