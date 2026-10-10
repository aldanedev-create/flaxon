from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Base adapter implementation for the database subsystem."""

    @abstractmethod
    async def connect(self) -> None:
        """Open the configured connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the configured connection."""
        pass

    @abstractmethod
    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        pass

    @abstractmethod
    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        pass

    @abstractmethod
    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        pass

    @abstractmethod
    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        pass

    @abstractmethod
    async def begin(self) -> None:
        """Perform the begin operation for base adapter."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Perform the commit operation for base adapter."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Perform the rollback operation for base adapter."""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Perform the ping operation for base adapter."""
        pass
