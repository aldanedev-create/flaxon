from __future__ import annotations

from typing import Any

from flaxon._imports import import_attribute, import_module

from .base import BaseAdapter


class MySQLAdapter(BaseAdapter):
    """My sqladapter implementation for the database subsystem."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "mysql",
        user: str = "root",
        password: str = "",
        **kwargs: Any,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.kwargs = kwargs
        self._conn = None

    async def connect(self) -> None:
        """Open the configured connection."""
        try:
            aiomysql = import_module("aiomysql")

            self._conn = await aiomysql.connect(
                host=self.host,
                port=self.port,
                db=self.database,
                user=self.user,
                password=self.password,
                **self.kwargs,
            )
        except ImportError as exc:
            raise RuntimeError("aiomysql is required for MySQL. Install with: pip install aiomysql") from exc

    async def disconnect(self) -> None:
        """Close the configured connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        async with self._conn.cursor() as cursor:
            await cursor.execute(query, args)
            await self._conn.commit()
            return cursor

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        dict_cursor_type = import_attribute("aiomysql", "DictCursor")

        async with self._conn.cursor(dict_cursor_type) as cursor:
            await cursor.execute(query, args)
            return await cursor.fetchone()

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        dict_cursor_type = import_attribute("aiomysql", "DictCursor")

        async with self._conn.cursor(dict_cursor_type) as cursor:
            await cursor.execute(query, args)
            return await cursor.fetchall()

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        async with self._conn.cursor() as cursor:
            await cursor.execute(query, args)
            row = await cursor.fetchone()
            return row[0] if row else None

    async def begin(self) -> None:
        """Perform the begin operation for my sqladapter."""
        await self._conn.begin()

    async def commit(self) -> None:
        """Perform the commit operation for my sqladapter."""
        await self._conn.commit()

    async def rollback(self) -> None:
        """Perform the rollback operation for my sqladapter."""
        await self._conn.rollback()

    async def ping(self) -> bool:
        """Perform the ping operation for my sqladapter."""
        try:
            await self.fetch_val("SELECT 1")
            return True
        except Exception:
            return False
