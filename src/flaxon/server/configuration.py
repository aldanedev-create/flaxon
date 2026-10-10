from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServerConfig:
    """Server config implementation for the server subsystem."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    env: str = "development"
    log_level: str = "info"
    timeout_keep_alive: int = 5
    timeout_graceful_shutdown: int = 30
    ssl_keyfile: str | None = None
    ssl_certfile: str | None = None
    ssl_ca_certs: str | None = None
    proxy_headers: bool = True
    forwarded_allow_ips: str = "127.0.0.1"
    access_log: bool = True
    use_colors: bool = True
    loop: str = "asyncio"
    http: str = "auto"
    ws: str = "auto"
    lifespan: str = "auto"
    backlog: int = 2048
    limit_concurrency: int | None = None
    limit_max_requests: int | None = None
    app_dir: str = field(default_factory=os.getcwd)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._load_from_env()

    def _load_from_env(self) -> None:
        self.host = os.environ.get("FLAXON_HOST", self.host)
        self.port = int(os.environ.get("FLAXON_PORT", self.port))
        self.env = os.environ.get("FLAXON_ENV", self.env)
        self.log_level = os.environ.get("FLAXON_LOG_LEVEL", self.log_level)
        self.workers = int(os.environ.get("FLAXON_WORKERS", self.workers))

        if os.environ.get("FLAXON_RELOAD", "").lower() in {"true", "1", "yes"}:
            self.reload = True

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "host": self.host,
            "port": self.port,
            "reload": self.reload,
            "workers": self.workers,
            "env": self.env,
            "log_level": self.log_level,
            "timeout_keep_alive": self.timeout_keep_alive,
            "timeout_graceful_shutdown": self.timeout_graceful_shutdown,
            "ssl_keyfile": self.ssl_keyfile,
            "ssl_certfile": self.ssl_certfile,
            "ssl_ca_certs": self.ssl_ca_certs,
            "proxy_headers": self.proxy_headers,
            "forwarded_allow_ips": self.forwarded_allow_ips,
            "access_log": self.access_log,
            "use_colors": self.use_colors,
            "loop": self.loop,
            "http": self.http,
            "ws": self.ws,
            "lifespan": self.lifespan,
            "backlog": self.backlog,
            "limit_concurrency": self.limit_concurrency,
            "limit_max_requests": self.limit_max_requests,
            "app_dir": self.app_dir,
            **self.extra,
        }

    def is_development(self) -> bool:
        """Return whether development holds for the current value."""
        return self.env == "development"

    def is_production(self) -> bool:
        """Return whether production holds for the current value."""
        return self.env == "production"

    def is_testing(self) -> bool:
        """Return whether testing holds for the current value."""
        return self.env == "testing"
