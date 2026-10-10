from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from flaxon.http import JSONResponse


class RateLimiter:
    """Rate limiter implementation for the security subsystem."""

    def __init__(
        self,
        requests: int = 60,
        window_seconds: int = 60,
        key_func: Callable[[dict[str, Any]], str] | None = None,
    ) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    def _default_key(self, scope: dict[str, Any]) -> str:
        client = scope.get("client") or ("unknown", 0)
        return str(client[0])

    async def check(self, scope: dict[str, Any]) -> bool:
        """Perform the check operation for rate limiter."""
        key = self.key_func(scope)
        now = time.monotonic()

        async with self.lock:
            bucket = self.hits[key]
            cutoff = now - self.window_seconds

            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.requests:
                return False

            bucket.append(now)
            return True

    def get_remaining(self, scope: dict[str, Any]) -> int:
        """Return the remaining."""
        key = self.key_func(scope)
        now = time.monotonic()
        bucket = self.hits.get(key, deque())
        cutoff = now - self.window_seconds

        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        return max(0, self.requests - len(bucket))

    def get_retry_after(self, scope: dict[str, Any]) -> int:
        """Return the retry after."""
        key = self.key_func(scope)
        now = time.monotonic()
        bucket = self.hits.get(key, deque())

        if len(bucket) < self.requests:
            return 0

        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) < self.requests:
            return 0

        return int(bucket[0] + self.window_seconds - now) + 1


class RateLimitMiddleware:
    """Rate limit middleware implementation for the security subsystem."""

    def __init__(
        self,
        app: Any,
        requests: int = 60,
        window_seconds: int = 60,
        key_func: Callable[[dict[str, Any]], str] | None = None,
    ) -> None:
        self.app = app
        self.limiter = RateLimiter(requests, window_seconds, key_func)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        allowed = await self.limiter.check(scope)

        if not allowed:
            retry_after = self.limiter.get_retry_after(scope)
            response = JSONResponse(
                {
                    "success": False,
                    "error": {
                        "code": "FX-RATE-001",
                        "message": "Too many requests. Please try again later.",
                    },
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class DistributedRateLimiter:
    """Distributed rate limiter implementation for the security subsystem."""

    def __init__(self, redis_client: Any, prefix: str = "rate_limit") -> None:
        self.redis = redis_client
        self.prefix = prefix

    async def check(
        self,
        key: str,
        requests: int = 60,
        window_seconds: int = 60,
    ) -> bool:
        """Perform the check operation for distributed rate limiter."""
        full_key = f"{self.prefix}:{key}"
        now = time.time()
        window_start = now - window_seconds
        # The member must be unique.  A whole-second timestamp causes Redis
        # ZADD to overwrite same-second requests instead of counting them.
        member = str(time.time_ns())

        pipeline = self.redis.pipeline()
        pipeline.zremrangebyscore(full_key, 0, window_start)
        pipeline.zcard(full_key)
        pipeline.zadd(full_key, {member: now})
        pipeline.expire(full_key, window_seconds)
        results = await pipeline.execute()

        count = results[1]
        return count < requests

    async def get_remaining(self, key: str, requests: int = 60, window_seconds: int = 60) -> int:
        """Return the remaining."""
        full_key = f"{self.prefix}:{key}"
        now = int(time.time())
        window_start = now - window_seconds

        await self.redis.zremrangebyscore(full_key, 0, window_start)
        count = await self.redis.zcard(full_key)
        return max(0, requests - count)

    async def get_retry_after(self, key: str, requests: int = 60, window_seconds: int = 60) -> int:
        """Return the retry after."""
        full_key = f"{self.prefix}:{key}"
        now = int(time.time())
        window_start = now - window_seconds

        await self.redis.zremrangebyscore(full_key, 0, window_start)
        count = await self.redis.zcard(full_key)

        if count < requests:
            return 0

        oldest = await self.redis.zrange(full_key, 0, 0, withscores=True)
        if oldest:
            oldest_time = int(oldest[0][1])
            return max(1, oldest_time + window_seconds - now)

        return 1
