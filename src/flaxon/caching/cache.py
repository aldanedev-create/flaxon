from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any


class Cache:
    def __init__(self, default_ttl: int = 300) -> None:
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, float, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            if key not in self._cache:
                return default

            value, expires, _ = self._cache[key]
            if expires is not None and time.time() > expires:
                del self._cache[key]
                return default

            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl or self.default_ttl
        expires = time.time() + ttl if ttl > 0 else None
        async with self._lock:
            self._cache[key] = (value, expires, time.time())

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key not in self._cache:
                return False

            value, expires, _ = self._cache[key]
            if expires is not None and time.time() > expires:
                del self._cache[key]
                return False

            return True

    async def get_or_set(self, key: str, func: Callable, ttl: int | None = None) -> Any:
        value = await self.get(key)
        if value is not None:
            return value

        if asyncio.iscoroutinefunction(func):
            value = await func()
        else:
            loop = asyncio.get_running_loop()
            value = await loop.run_in_executor(None, func)

        await self.set(key, value, ttl)
        return value

    async def increment(self, key: str, amount: int = 1) -> int:
        async with self._lock:
            now = time.time()
            entry = self._cache.get(key)
            if entry is not None:
                value, expires, created = entry
                if expires is not None and now > expires:
                    entry = None

            if entry is None:
                new_value = amount
                expires = now + self.default_ttl if self.default_ttl > 0 else None
                self._cache[key] = (new_value, expires, now)
                return new_value

            value, expires, created = entry
            new_value = int(value) + amount
            self._cache[key] = (new_value, expires, created)
            return new_value

    async def decrement(self, key: str, amount: int = 1) -> int:
        return await self.increment(key, -amount)

    async def expire(self, key: str, ttl: int) -> None:
        async with self._lock:
            if key not in self._cache:
                return

            value, _, created = self._cache[key]
            expires = time.time() + ttl if ttl > 0 else None
            self._cache[key] = (value, expires, created)

    async def touch(self, key: str) -> None:
        async with self._lock:
            if key not in self._cache:
                return

            value, expires, created = self._cache[key]
            if expires is not None:
                expires = time.time() + (expires - created)
                self._cache[key] = (value, expires, created)

    async def get_many(self, *keys: str) -> dict[str, Any]:
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_many(self, *keys: str) -> None:
        for key in keys:
            await self.delete(key)

    def get_stats(self) -> dict[str, Any]:
        total = len(self._cache)
        expired = 0
        current_time = time.time()

        for _, expires, _ in self._cache.values():
            if expires is not None and current_time > expires:
                expired += 1

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
        }

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)
