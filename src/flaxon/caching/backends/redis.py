from __future__ import annotations

import json
from typing import Any


class RedisBackend:
    """Store cache entries using an optional Redis client."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "flaxon:cache",
        decode_responses: bool = True,
    ) -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        self.decode_responses = decode_responses
        self._client = None

    async def connect(self) -> None:
        """Open the backend connection when it is needed."""
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self.redis_url,
                decode_responses=self.decode_responses,
            )
        except ImportError as exc:
            raise RuntimeError("redis is required. Install with: pip install redis") from exc

    async def disconnect(self) -> None:
        """Close the backend connection and release its client."""
        if self._client:
            await self._client.close()
            self._client = None

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, default=str, ensure_ascii=False)

    def _deserialize(self, value: str) -> Any:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str) -> Any:
        """Read a cached value through this storage backend."""
        value = await self._client.get(self._key(key))
        if value is None:
            return None
        return self._deserialize(value)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with the supplied expiration settings."""
        serialized = self._serialize(value)
        if ttl and ttl > 0:
            await self._client.setex(self._key(key), ttl, serialized)
        else:
            await self._client.set(self._key(key), serialized)

    async def delete(self, key: str) -> None:
        """Remove a cache entry if it exists."""
        await self._client.delete(self._key(key))

    async def clear(self) -> None:
        """Remove cache entries managed by this backend."""
        pattern = f"{self.prefix}:*"
        keys = await self._client.keys(pattern)
        if keys:
            await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check whether a key has an unexpired cache entry."""
        return bool(await self._client.exists(self._key(key)))

    async def expire(self, key: str, ttl: int) -> None:
        """Change the expiration of an existing cache entry."""
        await self._client.expire(self._key(key), ttl)

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Read multiple keys and return their available values."""
        full_keys = [self._key(k) for k in keys]
        values = await self._client.mget(full_keys)

        result = {}
        for key, value in zip(keys, values, strict=True):
            if value is not None:
                result[key] = self._deserialize(value)
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Store multiple key-value pairs with the supplied expiration settings."""
        pipe = self._client.pipeline()
        for key, value in items.items():
            serialized = self._serialize(value)
            if ttl and ttl > 0:
                pipe.setex(self._key(key), ttl, serialized)
            else:
                pipe.set(self._key(key), serialized)
        await pipe.execute()

    async def delete_many(self, keys: list[str]) -> None:
        """Remove the requested cache keys."""
        if keys:
            full_keys = [self._key(k) for k in keys]
            await self._client.delete(*full_keys)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increase a numeric cache value by the requested amount."""
        return await self._client.incrby(self._key(key), amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrease a numeric cache value by the requested amount."""
        return await self._client.decrby(self._key(key), amount)

    async def ttl(self, key: str) -> int:
        """Return the Redis time-to-live value for a cache key."""
        return await self._client.ttl(self._key(key))

    def get_stats(self) -> dict[str, Any]:
        """Return cache entry counts or backend statistics."""
        return {
            "backend": "redis",
            "url": self.redis_url,
        }
