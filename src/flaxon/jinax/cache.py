from __future__ import annotations

import hashlib
import time
from typing import Any


class TemplateCache:
    """Template cache implementation for the jinax subsystem."""

    def __init__(self, max_size: int = 100) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Retrieve the requested value using this object's configured behavior."""
        if key in self._cache:
            template, _timestamp = self._cache[key]
            self._hits += 1
            return template
        self._misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Store the supplied value under its key."""
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        """Perform the invalidate operation for template cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove the stored entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
        self._cache.pop(oldest_key, None)

    @property
    def size(self) -> int:
        """Return the configured size."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Return the configured hit rate."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


class CacheKeyBuilder:
    """Cache key builder implementation for the jinax subsystem."""

    @staticmethod
    def build_key(template_name: str, context: dict[str, Any]) -> str:
        """Build the key."""
        context_str = "".join(f"{k}:{v}" for k, v in sorted(context.items()))
        combined = f"{template_name}:{context_str}"
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()

    @staticmethod
    def build_template_key(template_name: str) -> str:
        """Build the template key."""
        return f"template:{template_name}"


class CachedTemplate:
    """Cached template implementation for the jinax subsystem."""

    def __init__(self, template: Any, cache_key: str, ttl: int = 300) -> None:
        self.template = template
        self.cache_key = cache_key
        self.ttl = ttl
        self._created = time.time()

    def is_expired(self) -> bool:
        """Return whether expired holds for the current value."""
        return time.time() - self._created > self.ttl


class CacheMiddleware:
    """Cache middleware implementation for the jinax subsystem."""

    def __init__(self, app: Any, cache: TemplateCache | None = None) -> None:
        self.app = app
        self.cache = cache or TemplateCache()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
