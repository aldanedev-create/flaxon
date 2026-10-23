"""Pluggable broadcast medium for the realtime hub.

The hub publishes events to a Broadcaster and subscribes to receive them back.
Two implementations:

- ``MemoryBroadcaster`` keeps subscribers in process memory. If two hubs share
  ONE instance, events cross "workers" (used to simulate multi-worker in tests
  without Redis). If each hub gets its OWN instance, events stay local — that is
  exactly the naive, broken, single-process behaviour the course demonstrates.
- ``RedisBackedBroadcaster`` wraps Flaxon's ``RedisBroadcaster`` so events cross
  real OS processes via Redis Pub/Sub.
"""
from __future__ import annotations

import abc
import asyncio
from collections import defaultdict


class Broadcaster(abc.ABC):
    @abc.abstractmethod
    async def publish(self, channel: str, message: dict) -> None: ...

    @abc.abstractmethod
    def subscribe(self, channel: str):
        """Return an async iterator yielding messages published to `channel`."""
        ...

    async def close(self) -> None:  # pragma: no cover - opt-in cleanup
        return None


class MemoryBroadcaster(Broadcaster):
    """In-process pub/sub. Scope is per instance, which is the whole point."""

    def __init__(self, max_queue: int = 1024) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._max_queue = max_queue

    async def publish(self, channel: str, message: dict) -> None:
        for queue in list(self._subscribers.get(channel, ())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Drop rather than block the publisher; ephemeral traffic only.
                try:
                    queue.get_nowait()
                    queue.put_nowait(message)
                except asyncio.QueueEmpty:
                    pass

    def subscribe(self, channel: str):
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers[channel].add(queue)

        async def generator():
            try:
                while True:
                    yield await queue.get()
            finally:
                self._subscribers[channel].discard(queue)

        return generator()


class RedisBackedBroadcaster(Broadcaster):
    """Redis Pub/Sub bridge. One connection pair is created lazily per instance."""

    def __init__(self, redis_url: str) -> None:
        from flaxon.websocket.redis_backend import RedisBroadcaster

        self._impl = RedisBroadcaster(redis_url)
        self._redis_url = redis_url

    async def publish(self, channel: str, message: dict) -> None:
        await self._impl.publish(channel, message)

    def subscribe(self, channel: str):
        return self._impl.subscribe(channel)

    async def close(self) -> None:  # pragma: no cover - needs a live Redis
        for attr in ("_pub", "_sub"):
            client = getattr(self._impl, attr, None)
            if client is not None:
                try:
                    await client.close()
                except Exception:
                    pass
