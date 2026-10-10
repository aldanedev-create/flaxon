from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from flaxon._imports import import_module

from .broadcaster import Broadcaster


class RedisBroadcaster(Broadcaster):
    """Redis broadcaster implementation for the websocket subsystem."""

    def __init__(
        self, redis_url: str = "redis://localhost:6379/0", *, protocol: int = 2, max_connections: int = 100
    ) -> None:
        self.redis_url = redis_url
        self.protocol = protocol
        self.max_connections = max_connections
        self._pub = None
        self._sub = None
        self._lock = asyncio.Lock()

    async def _get_pub(self):
        if self._pub is None:
            redis = import_module("redis.asyncio")

            self._pub = redis.from_url(
                self.redis_url,
                decode_responses=True,
                protocol=self.protocol,
                max_connections=self.max_connections,
            )
        return self._pub

    async def _get_sub(self):
        if self._sub is None:
            redis = import_module("redis.asyncio")

            self._sub = redis.from_url(
                self.redis_url,
                decode_responses=True,
                protocol=self.protocol,
                max_connections=self.max_connections,
            )
        return self._sub

    async def publish(self, channel: str, message: Any) -> None:
        """Perform the publish operation for redis broadcaster."""
        pub = await self._get_pub()
        if not isinstance(message, str):
            message = json.dumps(message)
        await pub.publish(channel, message)

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        """Register a subscription for the supplied event or operation."""
        sub = await self._get_sub()
        pubsub = sub.pubsub()
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    try:
                        yield json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        yield data
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


class RedisBackend:
    """Provide redis storage for flaxon operations."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_url = redis_url
        self._client = None
        self._lock = asyncio.Lock()

    async def get_client(self):
        """Return the client."""
        if self._client is None:
            redis = import_module("redis.asyncio")

            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store the supplied value under its key."""
        client = await self.get_client()
        if not isinstance(value, str):
            value = json.dumps(value)
        if ttl:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)

    async def get(self, key: str) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        client = await self.get_client()
        value = await client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def delete(self, key: str) -> None:
        """Delete the specified entry from the configured store."""
        client = await self.get_client()
        await client.delete(key)

    async def exists(self, key: str) -> bool:
        """Return whether the requested entry exists."""
        client = await self.get_client()
        return bool(await client.exists(key))

    async def expire(self, key: str, ttl: int) -> None:
        """Perform the expire operation for redis backend."""
        client = await self.get_client()
        await client.expire(key, ttl)

    async def incr(self, key: str) -> int:
        """Perform the incr operation for redis backend."""
        client = await self.get_client()
        return await client.incr(key)

    async def decr(self, key: str) -> int:
        """Perform the decr operation for redis backend."""
        client = await self.get_client()
        return await client.decr(key)

    async def sadd(self, key: str, *values: Any) -> None:
        """Perform the sadd operation for redis backend."""
        client = await self.get_client()
        await client.sadd(key, *values)

    async def srem(self, key: str, *values: Any) -> None:
        """Perform the srem operation for redis backend."""
        client = await self.get_client()
        await client.srem(key, *values)

    async def smembers(self, key: str) -> set:
        """Perform the smembers operation for redis backend."""
        client = await self.get_client()
        return await client.smembers(key)

    async def sismember(self, key: str, value: Any) -> bool:
        """Perform the sismember operation for redis backend."""
        client = await self.get_client()
        return bool(await client.sismember(key, value))

    async def lpush(self, key: str, *values: Any) -> None:
        """Perform the lpush operation for redis backend."""
        client = await self.get_client()
        await client.lpush(key, *values)

    async def rpush(self, key: str, *values: Any) -> None:
        """Perform the rpush operation for redis backend."""
        client = await self.get_client()
        await client.rpush(key, *values)

    async def lpop(self, key: str) -> Any:
        """Perform the lpop operation for redis backend."""
        client = await self.get_client()
        value = await client.lpop(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def rpop(self, key: str) -> Any:
        """Perform the rpop operation for redis backend."""
        client = await self.get_client()
        value = await client.rpop(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def lrange(self, key: str, start: int, stop: int) -> list:
        """Perform the lrange operation for redis backend."""
        client = await self.get_client()
        values = await client.lrange(key, start, stop)
        result = []
        for value in values:
            try:
                result.append(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                result.append(value)
        return result

    async def hset(self, key: str, field: str, value: Any) -> None:
        """Perform the hset operation for redis backend."""
        client = await self.get_client()
        if not isinstance(value, str):
            value = json.dumps(value)
        await client.hset(key, field, value)

    async def hget(self, key: str, field: str) -> Any:
        """Perform the hget operation for redis backend."""
        client = await self.get_client()
        value = await client.hget(key, field)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def hgetall(self, key: str) -> dict:
        """Perform the hgetall operation for redis backend."""
        client = await self.get_client()
        data = await client.hgetall(key)
        result = {}
        for field, value in data.items():
            try:
                result[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[field] = value
        return result

    async def hdel(self, key: str, *fields: str) -> None:
        """Perform the hdel operation for redis backend."""
        client = await self.get_client()
        await client.hdel(key, *fields)

    async def close(self) -> None:
        """Release the resources held by this object."""
        if self._client:
            await self._client.close()
            self._client = None
