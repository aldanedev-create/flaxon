"""The application context: process-wide collaborators shared by every module.

Modules receive this object through Flaxon's dependency-injection container
(``app.container.register_instance("ctx", ctx)``) and declare the dependency with
``module.requires("ctx")``, so mounting a module on an app that forgot to build a
context fails loudly at startup instead of on the first request.

Everything here wraps a *verified* Flaxon primitive rather than reinventing it:

- ``CSRF``            -> ``flaxon.security.csrf.CSRF`` (HMAC token, 1h lifetime)
- ``RateLimiter``     -> ``flaxon.security.rate_limit.RateLimiter`` (async, per-key)
- broadcaster         -> ``services.broadcaster`` (Memory in dev, Redis in prod)
- hub                 -> ``services.hub.ChannelHub`` (per-process socket registry)
"""
from __future__ import annotations

import os

from flaxon.exceptions import TooManyRequests
from flaxon.security.csrf import CSRF
from flaxon.security.rate_limit import RateLimiter

from services.broadcaster import Broadcaster, MemoryBroadcaster
from services.hub import ChannelHub


def _client_ip(scope: dict) -> str:
    """Best-effort client identifier used to key rate-limit buckets."""
    headers = scope.get("headers") or []
    for raw_name, raw_value in headers:
        if raw_name.decode("latin-1").lower() == "x-forwarded-for":
            return raw_value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


class AppContext:
    """Holds the collaborators a request handler needs but should not build."""

    def __init__(self, *, secret_key: str, broadcaster: Broadcaster | None = None) -> None:
        self.secret_key = secret_key
        # Rate limiting is a real security control, but it is process-local and
        # keyed by client IP; tests share one IP, so it can be disabled via env
        # (RATE_LIMIT_ENABLED=false) without changing the application code paths.
        self.rate_limit_enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false"
        self.csrf = CSRF(secret_key=secret_key)
        self.broadcaster: Broadcaster = broadcaster or MemoryBroadcaster()
        self.hub = ChannelHub(self.broadcaster)
        self._limiters: dict[str, RateLimiter] = {}

    # -- rate limiting -----------------------------------------------------

    def _limiter(self, bucket: str, limit: tuple[int, int]) -> RateLimiter:
        key = f"{bucket}:{limit[0]}:{limit[1]}"
        limiter = self._limiters.get(key)
        if limiter is None:
            limiter = RateLimiter(
                requests=limit[0],
                window_seconds=limit[1],
                key_func=lambda scope: f"{bucket}:{_client_ip(scope)}",
            )
            self._limiters[key] = limiter
        return limiter

    async def guard(self, request, bucket: str, limit: tuple[int, int] | None) -> None:
        """Enforce ``(max_requests, window_seconds)`` for this client.

        Raises ``TooManyRequests`` (429) when the bucket is exhausted. Passing
        ``limit=None`` disables the check, which is how the tests run without
        tripping the demo limits. Rate limiting can also be switched off for the
        whole process with RATE_LIMIT_ENABLED=false.
        """
        if limit is None or not self.rate_limit_enabled:
            return
        if not await self._limiter(bucket, limit).check(request.scope or {}):
            raise TooManyRequests("Too many requests — slow down and retry later")

    # -- lifecycle ---------------------------------------------------------

    async def startup(self) -> None:
        await self.hub.start()

    async def shutdown(self) -> None:
        await self.hub.shutdown()
        await self.broadcaster.close()
