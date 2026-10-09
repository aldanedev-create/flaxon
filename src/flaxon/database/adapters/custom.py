from __future__ import annotations

import inspect
from typing import Any

from .base import BaseAdapter


class CustomAdapter(BaseAdapter):
    def __init__(self, connection: Any) -> None:
        self._conn = connection

    async def connect(self) -> None:
        if hasattr(self._conn, "connect"):
            result = self._conn.connect()
            if inspect.isawaitable(result):
                await result

    async def disconnect(self) -> None:
        if hasattr(self._conn, "disconnect"):
            result = self._conn.disconnect()
            if inspect.isawaitable(result):
                await result
        elif hasattr(self._conn, "close"):
            result = self._conn.close()
            if inspect.isawaitable(result):
                await result

    async def execute(self, query: str, *args: Any) -> Any:
        if hasattr(self._conn, "execute"):
            result = self._conn.execute(query, *args)
            return await result if inspect.isawaitable(result) else result
        raise NotImplementedError("Custom adapter does not support execute")

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        if hasattr(self._conn, "fetch_one"):
            result = self._conn.fetch_one(query, *args)
            return await result if inspect.isawaitable(result) else result
        raise NotImplementedError("Custom adapter does not support fetch_one")

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if hasattr(self._conn, "fetch_all"):
            result = self._conn.fetch_all(query, *args)
            return await result if inspect.isawaitable(result) else result
        raise NotImplementedError("Custom adapter does not support fetch_all")

    async def fetch_val(self, query: str, *args: Any) -> Any:
        if hasattr(self._conn, "fetch_val"):
            result = self._conn.fetch_val(query, *args)
            return await result if inspect.isawaitable(result) else result
        raise NotImplementedError("Custom adapter does not support fetch_val")

    async def begin(self) -> None:
        if hasattr(self._conn, "begin"):
            result = self._conn.begin()
            if inspect.isawaitable(result):
                await result

    async def commit(self) -> None:
        if hasattr(self._conn, "commit"):
            result = self._conn.commit()
            if inspect.isawaitable(result):
                await result

    async def rollback(self) -> None:
        if hasattr(self._conn, "rollback"):
            result = self._conn.rollback()
            if inspect.isawaitable(result):
                await result

    async def ping(self) -> bool:
        try:
            await self.fetch_val("SELECT 1")
            return True
        except Exception:
            return False
