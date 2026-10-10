from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from flaxon._imports import import_module


class DatabaseConnection(ABC):
    """Database connection implementation for the database subsystem."""

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


class ConnectionPool:
    """Connection pool implementation for the database subsystem."""

    def __init__(
        self,
        connection_class: type[DatabaseConnection],
        min_size: int = 5,
        max_size: int = 20,
        **kwargs: Any,
    ) -> None:
        self.connection_class = connection_class
        self.min_size = min_size
        self.max_size = max_size
        self.kwargs = kwargs
        self._pool: asyncio.Queue[DatabaseConnection] = asyncio.Queue()
        self._size = 0
        self._lock = asyncio.Lock()
        self._closed = False

    async def initialize(self) -> None:
        """Prepare the configured resources for use."""
        async with self._lock:
            for _ in range(self.min_size):
                conn = self.connection_class(**self.kwargs)
                await conn.connect()
                await self._pool.put(conn)
                self._size += 1

    async def acquire(self) -> DatabaseConnection:
        """Perform the acquire operation for connection pool."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            async with self._lock:
                if self._size < self.max_size:
                    conn = self.connection_class(**self.kwargs)
                    await conn.connect()
                    self._size += 1
                    return conn
                return await self._pool.get()

    async def release(self, conn: DatabaseConnection) -> None:
        """Perform the release operation for connection pool."""
        if self._closed:
            await conn.disconnect()
            return
        await self._pool.put(conn)

    async def close(self) -> None:
        """Release the resources held by this object."""
        self._closed = True
        while not self._pool.empty():
            conn = await self._pool.get()
            await conn.disconnect()
        self._size = 0

    @property
    def size(self) -> int:
        """Return the configured size."""
        return self._size

    @property
    def available(self) -> int:
        """Return the configured available."""
        return self._pool.qsize()


class PostgresConnection(DatabaseConnection):
    """Postgres connection implementation for the database subsystem."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        password: str = "",
        **kwargs: Any,
    ) -> None:
        """Perform the   init   operation for postgres connection."""
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


class SQLiteConnection(DatabaseConnection):
    """Sqlite connection implementation for the database subsystem."""

    def __init__(self, database: str = ":memory:", **kwargs: Any) -> None:
        """Perform the   init   operation for sqlite connection."""
        self.database = database
        self.kwargs = kwargs
        self._conn = None

    async def connect(self) -> None:
        """Open the configured connection."""
        try:
            aiosqlite = import_module("aiosqlite")

            self._conn = await aiosqlite.connect(self.database, **self.kwargs)
        except ImportError as exc:
            raise RuntimeError(
                "aiosqlite is required for SQLite. Install with: pip install aiosqlite"
            ) from exc

    async def disconnect(self) -> None:
        """Close the configured connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        cursor = await self._conn.execute(query, args)
        await self._conn.commit()
        return cursor

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        cursor = await self._conn.execute(query, args)
        row = await cursor.fetchone()
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row, strict=True))

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        cursor = await self._conn.execute(query, args)
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        cursor = await self._conn.execute(query, args)
        row = await cursor.fetchone()
        return row[0] if row else None
