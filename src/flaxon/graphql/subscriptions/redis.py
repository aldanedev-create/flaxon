from __future__ import annotations

import json
from typing import Any


class RedisSubscriptionBackend:
    def __init__(
        self, redis_url: str = "redis://localhost:6379/0", prefix: str = "graphql:subscription"
    ) -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        self._client = None
        self._pub = None
        self._sub = None
        self._sub_map: dict[str, str] = {}

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(self.redis_url, decode_responses=True)
            self._pub = redis.from_url(self.redis_url, decode_responses=True)
            self._sub = redis.from_url(self.redis_url, decode_responses=True)
        except ImportError as exc:
            raise RuntimeError(
                "redis package is required for RedisSubscriptionBackend. Install with: pip install redis"
            ) from exc

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        if self._pub:
            await self._pub.close()
            self._pub = None
        if self._sub:
            await self._sub.close()
            self._sub = None

    def _key(self, operation_id: str) -> str:
        return f"{self.prefix}:{operation_id}"

    async def subscribe(self, operation_id: str, context: Any, variables: dict[str, Any]) -> str:
        import uuid

        subscription_id = str(uuid.uuid4())
        self._sub_map[subscription_id] = operation_id

        data = {
            "subscription_id": subscription_id,
            "operation_id": operation_id,
            "variables": variables,
        }

        if self._client:
            await self._client.hset(
                self._key(operation_id),
                subscription_id,
                json.dumps(data),
            )

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        operation_id = self._sub_map.pop(subscription_id, "")
        if operation_id and self._client:
            await self._client.hdel(self._key(operation_id), subscription_id)

    async def publish(self, operation_id: str, data: Any) -> None:
        if self._pub:
            await self._pub.publish(
                self._key(operation_id),
                json.dumps(data),
            )

    async def next(self, subscription_id: str) -> Any:
        operation_id = self._sub_map.get(subscription_id, "")
        if not operation_id or not self._sub:
            return None

        pubsub = self._sub.pubsub()
        await pubsub.subscribe(self._key(operation_id))

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    return json.loads(message["data"])
                if message["type"] == "unsubscribe":
                    break
        finally:
            await pubsub.unsubscribe(self._key(operation_id))

        return None
