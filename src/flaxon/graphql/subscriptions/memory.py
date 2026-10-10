from __future__ import annotations

import asyncio
import uuid
from typing import Any


class MemorySubscriptionBackend:
    """In-process subscription backend, matching RedisSubscriptionBackend's interface.

    Suitable for single-process deployments or local development. For multi-process
    or multi-server deployments, use RedisSubscriptionBackend instead so publishes
    from one process reach subscribers connected to another.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._sub_map: dict[str, str] = {}
        self._operation_subs: dict[str, set[str]] = {}

    async def connect(self) -> None:
        """No-op: nothing to connect to for the in-memory backend."""

    async def disconnect(self) -> None:
        """Release any pending queues."""
        self._queues.clear()
        self._sub_map.clear()
        self._operation_subs.clear()

    async def subscribe(self, operation_id: str, context: Any, variables: dict[str, Any]) -> str:
        """Register a subscription for the supplied event or operation."""
        subscription_id = str(uuid.uuid4())
        self._sub_map[subscription_id] = operation_id
        self._operation_subs.setdefault(operation_id, set()).add(subscription_id)
        self._queues[subscription_id] = asyncio.Queue()
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove the requested subscription."""
        operation_id = self._sub_map.pop(subscription_id, "")
        if operation_id in self._operation_subs:
            self._operation_subs[operation_id].discard(subscription_id)
            if not self._operation_subs[operation_id]:
                del self._operation_subs[operation_id]
        queue = self._queues.pop(subscription_id, None)
        if queue is not None:
            await queue.put(None)

    async def publish(self, operation_id: str, data: Any) -> None:
        """Perform the publish operation for memory subscription backend."""
        for subscription_id in self._operation_subs.get(operation_id, set()):
            queue = self._queues.get(subscription_id)
            if queue is not None:
                await queue.put(data)

    async def next(self, subscription_id: str) -> Any:
        """Perform the next operation for memory subscription backend."""
        queue = self._queues.get(subscription_id)
        if queue is None:
            return None
        return await queue.get()
