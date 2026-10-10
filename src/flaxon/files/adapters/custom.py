from __future__ import annotations

from typing import Any


class CustomStorageAdapter:
    """Custom storage adapter implementation for the files subsystem."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    async def write(self, path: str, data: bytes) -> None:
        """Perform the write operation for custom storage adapter."""
        if hasattr(self.adapter, "write"):
            result = self.adapter.write(path, data)
            if hasattr(result, "__await__"):
                await result
            return
        raise NotImplementedError("Adapter does not support write")

    async def read(self, path: str) -> bytes:
        """Perform the read operation for custom storage adapter."""
        if hasattr(self.adapter, "read"):
            result = self.adapter.read(path)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Adapter does not support read")

    async def delete(self, path: str) -> bool:
        """Delete the specified entry from the configured store."""
        if hasattr(self.adapter, "delete"):
            result = self.adapter.delete(path)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Adapter does not support delete")

    async def exists(self, path: str) -> bool:
        """Return whether the requested entry exists."""
        if hasattr(self.adapter, "exists"):
            result = self.adapter.exists(path)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Adapter does not support exists")

    async def size(self, path: str) -> int:
        """Perform the size operation for custom storage adapter."""
        if hasattr(self.adapter, "size"):
            result = self.adapter.size(path)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Adapter does not support size")

    async def list(self, path: str = "") -> list[str]:
        """Return the matching entries."""
        if hasattr(self.adapter, "list"):
            result = self.adapter.list(path)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Adapter does not support list")

    async def move(self, source: str, destination: str) -> None:
        """Perform the move operation for custom storage adapter."""
        if hasattr(self.adapter, "move"):
            result = self.adapter.move(source, destination)
            if hasattr(result, "__await__"):
                await result
            return
        raise NotImplementedError("Adapter does not support move")

    async def copy(self, source: str, destination: str) -> None:
        """Return a copy of the current value."""
        if hasattr(self.adapter, "copy"):
            result = self.adapter.copy(source, destination)
            if hasattr(result, "__await__"):
                await result
            return
        raise NotImplementedError("Adapter does not support copy")

    def get_url(self, path: str) -> str:
        """Return the url."""
        if hasattr(self.adapter, "get_url"):
            return self.adapter.get_url(path)
        return f"/uploads/{path}"
