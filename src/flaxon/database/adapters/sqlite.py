from __future__ import annotations

import re
from typing import Any

from .base import BaseAdapter


class SQLiteAdapter(BaseAdapter):
    def __init__(self, database: str = ":memory:", **kwargs: Any) -> None:
        self.database = database
        self.kwargs = kwargs
        self._conn = None
        self._in_transaction = False

    @staticmethod
    def _adapt(query: str, args: tuple[Any, ...]) -> tuple[str, tuple[Any, ...]]:
        """Translate PostgreSQL-style positional placeholders for SQLite."""
        positions = [int(match.group(1)) for match in re.finditer(r"\$(\d+)", query)]
        if not positions:
            return query, args
        return re.sub(r"\$(\d+)", "?", query), tuple(args[position - 1] for position in positions)

    async def connect(self) -> None:
        try:
            import aiosqlite

            self._conn = await aiosqlite.connect(self.database, **self.kwargs)
        except ImportError as exc:
            raise RuntimeError(
                "aiosqlite is required for SQLite. Install with: pip install aiosqlite"
            ) from exc

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, *args: Any) -> Any:
        query, args = self._adapt(query, args)
        cursor = await self._conn.execute(query, args)
        if not self._in_transaction:
            await self._conn.commit()
        return cursor

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        query, args = self._adapt(query, args)
        cursor = await self._conn.execute(query, args)
        row = await cursor.fetchone()
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row, strict=True))

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        query, args = self._adapt(query, args)
        cursor = await self._conn.execute(query, args)
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    async def fetch_val(self, query: str, *args: Any) -> Any:
        query, args = self._adapt(query, args)
        cursor = await self._conn.execute(query, args)
        row = await cursor.fetchone()
        return row[0] if row else None

    async def begin(self) -> None:
        await self._conn.execute("BEGIN")
        self._in_transaction = True

    async def commit(self) -> None:
        await self._conn.commit()
        self._in_transaction = False

    async def rollback(self) -> None:
        await self._conn.rollback()
        self._in_transaction = False

    async def ping(self) -> bool:
        try:
            await self.fetch_val("SELECT 1")
            return True
        except Exception:
            return False
