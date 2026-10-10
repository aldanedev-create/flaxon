from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any


class MemoryBackend:
    """Store cache entries in this process with background expiration cleanup."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, float, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start background cache-expiration cleanup."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Cancel and await background cache-expiration cleanup."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def get(self, key: str) -> Any:
        """Read a cached value through this storage backend."""
        async with self._lock:
            if key not in self._cache:
                return None

            value, expires, _ = self._cache[key]
            if expires is not None and time.time() > expires:
                del self._cache[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with the supplied expiration settings."""
        expires = time.time() + ttl if ttl and ttl > 0 else None
        async with self._lock:
            self._cache[key] = (value, expires, time.time())

    async def delete(self, key: str) -> None:
        """Remove a cache entry if it exists."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Remove cache entries managed by this backend."""
        async with self._lock:
            self._cache.clear()

    async def exists(self, key: str) -> bool:
        """Check whether a key has an unexpired cache entry."""
        async with self._lock:
            if key not in self._cache:
                return False

            _value, expires, _ = self._cache[key]
            if expires is not None and time.time() > expires:
                del self._cache[key]
                return False

            return True

    async def expire(self, key: str, ttl: int) -> None:
        """Change the expiration of an existing cache entry."""
        async with self._lock:
            if key not in self._cache:
                return

            value, _, created = self._cache[key]
            expires = time.time() + ttl if ttl > 0 else None
            self._cache[key] = (value, expires, created)

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Read multiple keys and return their available values."""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Store multiple key-value pairs with the supplied expiration settings."""
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_many(self, keys: list[str]) -> None:
        """Remove the requested cache keys."""
        for key in keys:
            await self.delete(key)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increase a numeric cache value by the requested amount."""
        async with self._lock:
            now = time.time()
            entry = self._cache.get(key)
            if entry is not None:
                _value, expires, _ = entry
                if expires is not None and now > expires:
                    entry = None

            new_value = amount if entry is None else int(entry[0]) + amount

            self._cache[key] = (new_value, None, now)
            return new_value

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrease a numeric cache value by the requested amount."""
        return await self.increment(key, -amount)

    async def _cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(60)
            current_time = time.time()
            async with self._lock:
                to_remove = []
                for key, (_, expires, _) in self._cache.items():
                    if expires is not None and current_time > expires:
                        to_remove.append(key)
                for key in to_remove:
                    self._cache.pop(key, None)

    def get_stats(self) -> dict[str, Any]:
        """Return cache entry counts or backend statistics."""
        current_time = time.time()
        total = len(self._cache)
        expired = 0
        for _, expires, _ in self._cache.values():
            if expires is not None and current_time > expires:
                expired += 1

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
        }

    def __len__(self) -> int:
        return len(self._cache)
