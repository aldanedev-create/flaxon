from __future__ import annotations

from typing import Any

from flaxon._imports import import_module

from .base import BaseAdapter


class RedisAdapter(BaseAdapter):
    """Redis adapter implementation for the database subsystem."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        database: int = 0,
        password: str | None = None,
        decode_responses: bool = True,
        **kwargs: Any,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.password = password
        self.decode_responses = decode_responses
        self.kwargs = kwargs
        self._client = None

    async def connect(self) -> None:
        """Open the configured connection."""
        try:
            redis = import_module("redis.asyncio")

            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.database,
                password=self.password,
                decode_responses=self.decode_responses,
                **self.kwargs,
            )
        except ImportError as exc:
            raise RuntimeError("redis is required. Install with: pip install redis") from exc

    async def disconnect(self) -> None:
        """Close the configured connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        raise NotImplementedError("Redis does not support SQL queries")

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        raise NotImplementedError("Redis does not support SQL queries")

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        raise NotImplementedError("Redis does not support SQL queries")

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        raise NotImplementedError("Redis does not support SQL queries")

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store the supplied value under its key."""
        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    async def get(self, key: str) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        return await self._client.get(key)

    async def delete(self, key: str) -> None:
        """Delete the specified entry from the configured store."""
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Return whether the requested entry exists."""
        return bool(await self._client.exists(key))

    async def expire(self, key: str, ttl: int) -> None:
        """Perform the expire operation for redis adapter."""
        await self._client.expire(key, ttl)

    async def incr(self, key: str) -> int:
        """Perform the incr operation for redis adapter."""
        return await self._client.incr(key)

    async def decr(self, key: str) -> int:
        """Perform the decr operation for redis adapter."""
        return await self._client.decr(key)

    async def hset(self, key: str, field: str, value: Any) -> None:
        """Perform the hset operation for redis adapter."""
        await self._client.hset(key, field, value)

    async def hget(self, key: str, field: str) -> Any:
        """Perform the hget operation for redis adapter."""
        return await self._client.hget(key, field)

    async def hgetall(self, key: str) -> dict[str, Any]:
        """Perform the hgetall operation for redis adapter."""
        return await self._client.hgetall(key)

    async def lpush(self, key: str, *values: Any) -> None:
        """Perform the lpush operation for redis adapter."""
        await self._client.lpush(key, *values)

    async def rpush(self, key: str, *values: Any) -> None:
        """Perform the rpush operation for redis adapter."""
        await self._client.rpush(key, *values)

    async def lpop(self, key: str) -> Any:
        """Perform the lpop operation for redis adapter."""
        return await self._client.lpop(key)

    async def rpop(self, key: str) -> Any:
        """Perform the rpop operation for redis adapter."""
        return await self._client.rpop(key)

    async def lrange(self, key: str, start: int, stop: int) -> list[Any]:
        """Perform the lrange operation for redis adapter."""
        return await self._client.lrange(key, start, stop)

    async def sadd(self, key: str, *values: Any) -> None:
        """Perform the sadd operation for redis adapter."""
        await self._client.sadd(key, *values)

    async def srem(self, key: str, *values: Any) -> None:
        """Perform the srem operation for redis adapter."""
        await self._client.srem(key, *values)

    async def smembers(self, key: str) -> set[Any]:
        """Perform the smembers operation for redis adapter."""
        return await self._client.smembers(key)

    async def begin(self) -> None:
        """Perform the begin operation for redis adapter."""
        pass

    async def commit(self) -> None:
        """Perform the commit operation for redis adapter."""
        pass

    async def rollback(self) -> None:
        """Perform the rollback operation for redis adapter."""
        pass

    async def ping(self) -> bool:
        """Perform the ping operation for redis adapter."""
        try:
            return bool(await self._client.ping())
        except Exception:
            return False
