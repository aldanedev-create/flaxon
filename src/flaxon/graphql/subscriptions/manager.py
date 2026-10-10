from __future__ import annotations

import asyncio
import uuid
from typing import Any

from .memory import MemorySubscriptionBackend


class SubscriptionManager:
    """Subscription manager implementation for the graphql subsystem."""

    def __init__(self, backend: Any = None) -> None:
        self.backend = backend or MemorySubscriptionBackend()
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, operation_id: str, context: Any, variables: dict[str, Any]) -> str:
        """Register a subscription for the supplied event or operation."""
        subscription_id = str(uuid.uuid4())

        async with self._lock:
            self._subscriptions[subscription_id] = {
                "operation_id": operation_id,
                "context": context,
                "variables": variables,
                "queue": asyncio.Queue(),
            }

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove the requested subscription."""
        async with self._lock:
            if subscription_id in self._subscriptions:
                queue = self._subscriptions[subscription_id].get("queue")
                if queue:
                    await queue.put(None)
                del self._subscriptions[subscription_id]

    async def publish(self, operation_id: str, data: Any) -> None:
        """Perform the publish operation for subscription manager."""
        async with self._lock:
            for _sub_id, sub in self._subscriptions.items():
                if sub["operation_id"] == operation_id:
                    queue = sub.get("queue")
                    if queue:
                        await queue.put(data)

    async def next(self, subscription_id: str) -> Any:
        """Perform the next operation for subscription manager."""
        sub = self._subscriptions.get(subscription_id)
        if sub is None:
            return None

        queue = sub.get("queue")
        if queue is None:
            return None

        return await queue.get()

    def get_subscription_count(self) -> int:
        """Return the subscription count."""
        return len(self._subscriptions)

    def get_subscriptions_by_operation(self, operation_id: str) -> list[str]:
        """Return the subscriptions by operation."""
        result = []
        for sub_id, sub in self._subscriptions.items():
            if sub["operation_id"] == operation_id:
                result.append(sub_id)
        return result
