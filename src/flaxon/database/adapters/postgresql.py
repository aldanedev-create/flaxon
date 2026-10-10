from __future__ import annotations

from typing import Any

from flaxon._imports import import_module

from .base import BaseAdapter


class PostgreSQLAdapter(BaseAdapter):
    """Postgre sqladapter implementation for the database subsystem."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
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
            asyncpg = import_module("asyncpg")

            self._conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                **self.kwargs,
            )
        except ImportError as exc:
            raise RuntimeError(
                "asyncpg is required for PostgreSQL. Install with: pip install asyncpg"
            ) from exc

    async def disconnect(self) -> None:
        """Close the configured connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        return await self._conn.execute(query, *args)

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        row = await self._conn.fetchrow(query, *args)
        return dict(row) if row else None

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        rows = await self._conn.fetch(query, *args)
        return [dict(row) for row in rows]

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        return await self._conn.fetchval(query, *args)

    async def begin(self) -> None:
        """Perform the begin operation for postgre sqladapter."""
        await self._conn.execute("BEGIN")

    async def commit(self) -> None:
        """Perform the commit operation for postgre sqladapter."""
        await self._conn.execute("COMMIT")

    async def rollback(self) -> None:
        """Perform the rollback operation for postgre sqladapter."""
        await self._conn.execute("ROLLBACK")

    async def ping(self) -> bool:
        """Perform the ping operation for postgre sqladapter."""
        try:
            await self.fetch_val("SELECT 1")
            return True
        except Exception:
            return False
