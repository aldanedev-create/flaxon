from __future__ import annotations

from typing import Any


class CustomAdapter:
    """Custom adapter implementation for the mail subsystem."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    async def send(self, email: Any) -> None:
        """Perform the send operation for custom adapter."""
        if hasattr(self.adapter, "send"):
            result = self.adapter.send(email)
            if hasattr(result, "__await__"):
                await result
            return
        raise NotImplementedError("Adapter does not support send")
