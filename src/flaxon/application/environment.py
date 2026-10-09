"""
Environment detection and management.

This module provides utilities for detecting and managing the runtime
environment.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class EnvironmentInfo:
    """
    Information about the current runtime environment.

    Attributes:
        env: The environment name.
        debug: Whether debug mode is enabled.
        python_version: Python version string.
        platform: Operating system name.
        hostname: The hostname of the machine.
        pid: The process ID.
        is_docker: Whether running in a Docker container.
        is_kubernetes: Whether running in Kubernetes.
        is_github_actions: Whether running in GitHub Actions.
    """

    env: str = "development"
    debug: bool = False
    python_version: str = ""
    platform: str = ""
    hostname: str = ""
    pid: int = 0
    is_docker: bool = False
    is_kubernetes: bool = False
    is_github_actions: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "env": self.env,
            "debug": self.debug,
            "python_version": self.python_version,
            "platform": self.platform,
            "hostname": self.hostname,
            "pid": self.pid,
            "is_docker": self.is_docker,
            "is_kubernetes": self.is_kubernetes,
            "is_github_actions": self.is_github_actions,
        }


class Environment:
    """Environment detection and management utility."""

    def __init__(self, env: str | None = None) -> None:
        """Initialize the environment."""
        self._env = env or os.environ.get("FLAXON_ENV", "development")
        self._debug = os.environ.get("FLAXON_DEBUG", "false").lower() in {"true", "1", "yes", "on"}

    @property
    def env(self) -> str:
        """Get the current environment name."""
        return self._env

    @env.setter
    def env(self, value: str) -> None:
        """Set the environment name."""
        self._env = value

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        """Set debug mode."""
        self._debug = value

    def is_development(self) -> bool:
        """Check if in development environment."""
        return self._env == "development"

    def is_testing(self) -> bool:
        """Check if in testing environment."""
        return self._env == "testing"

    def is_staging(self) -> bool:
        """Check if in staging environment."""
        return self._env == "staging"

    def is_production(self) -> bool:
        """Check if in production environment."""
        return self._env == "production"

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug

    def is_docker(self) -> bool:
        """Check if running in a Docker container."""
        return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

    def is_kubernetes(self) -> bool:
        """Check if running in Kubernetes."""
        return "KUBERNETES_SERVICE_HOST" in os.environ

    def is_github_actions(self) -> bool:
        """Check if running in GitHub Actions."""
        return os.environ.get("GITHUB_ACTIONS") == "true"

    def get_info(self) -> EnvironmentInfo:
        """Get comprehensive environment information."""
        return EnvironmentInfo(
            env=self._env,
            debug=self._debug,
            python_version=sys.version.split()[0],
            platform=platform.system(),
            hostname=platform.node(),
            pid=os.getpid(),
            is_docker=self.is_docker(),
            is_kubernetes=self.is_kubernetes(),
            is_github_actions=self.is_github_actions(),
        )

    def get_required(self, key: str) -> str:
        """Get a required environment variable."""
        value = os.environ.get(key)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value

    def get_optional(self, key: str, default: Any = None) -> Any:
        """Get an optional environment variable."""
        return os.environ.get(key, default)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get an integer environment variable."""
        value = os.environ.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"Environment variable '{key}' must be an integer") from exc

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        """Get a boolean environment variable."""
        value = os.environ.get(key)
        if value is None:
            return default
        return value.lower() in {"true", "1", "yes", "on", "enabled", "active"}

    def get_list(self, key: str, default: list[str] | None = None) -> list[str] | None:
        """Get a list environment variable (comma-separated)."""
        value = os.environ.get(key)
        if value is None:
            return default
        return [item.strip() for item in value.split(",") if item.strip()]

    def set_env_from_file(self, path: str) -> None:
        """Load environment variables from a .env file."""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
        except FileNotFoundError:
            pass


_default_env = Environment()


def get_env() -> Environment:
    """Get the default environment instance."""
    return _default_env


def set_env(env: str) -> None:
    """Set the environment name on the default instance."""
    _default_env.env = env


def set_debug(debug: bool) -> None:
    """Set debug mode on the default instance."""
    _default_env.debug = debug
