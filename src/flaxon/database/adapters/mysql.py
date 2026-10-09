from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class MySQLAdapter(BaseAdapter):
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
        try:
            import aiomysql
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
        if self._conn:
            self._conn.close()
            self._conn = None

    async def execute(self, query: str, *args: Any) -> Any:
        async with self._conn.cursor() as cursor:
            await cursor.execute(query, args)
            await self._conn.commit()
            return cursor

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        from aiomysql import DictCursor
        async with self._conn.cursor(DictCursor) as cursor:
            await cursor.execute(query, args)
            return await cursor.fetchone()

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        from aiomysql import DictCursor
        async with self._conn.cursor(DictCursor) as cursor:
            await cursor.execute(query, args)
            return await cursor.fetchall()

    async def fetch_val(self, query: str, *args: Any) -> Any:
        async with self._conn.cursor() as cursor:
            await cursor.execute(query, args)
            row = await cursor.fetchone()
            return row[0] if row else None

    async def begin(self) -> None:
        await self._conn.begin()

    async def commit(self) -> None:
        await self._conn.commit()

    async def rollback(self) -> None:
        await self._conn.rollback()

    async def ping(self) -> bool:
        try:
            await self.fetch_val("SELECT 1")
            return True
        except Exception:
            return False
