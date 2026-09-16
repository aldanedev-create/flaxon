"""Database manager for either a connection pool or a single adapter."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from .transactions import Transaction


class DatabaseManager:
    """Expose a uniform async database API over pools and adapters."""

    def __init__(self, pool: Any) -> None:
        self.pool = pool
        # Transaction state is task-local: requests sharing a manager must not
        # be treated as nested transactions.
        self._transaction_depth: ContextVar[int] = ContextVar("flaxon_transaction_depth", default=0)
        self._transaction_connection: ContextVar[Any | None] = ContextVar(
            "flaxon_transaction_connection", default=None
        )

    @property
    def _direct(self) -> bool:
        return not hasattr(self.pool, "acquire")

    async def initialize(self) -> None:
        if self._direct:
            await self.pool.connect()
        else:
            await self.pool.initialize()

    async def close(self) -> None:
        if self._direct:
            await self.pool.disconnect()
        else:
            await self.pool.close()

    async def _call(self, method: str, query: str, *args: Any) -> Any:
        if self._direct:
            return await getattr(self.pool, method)(query, *args)
        # Repository calls made inside ``async with db.transaction()`` must
        # stay on the transaction's leased connection. Acquiring a fresh
        # pooled connection here would make each statement commit outside the
        # surrounding transaction and break atomic multi-record writes.
        active_connection = self._transaction_connection.get()
        if active_connection is not None:
            return await getattr(active_connection, method)(query, *args)
        connection = await self.pool.acquire()
        try:
            return await getattr(connection, method)(query, *args)
        finally:
            await self.pool.release(connection)

    async def execute(self, query: str, *args: Any) -> Any:
        return await self._call("execute", query, *args)

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        return await self._call("fetch_one", query, *args)

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        return await self._call("fetch_all", query, *args)

    async def fetch_val(self, query: str, *args: Any) -> Any:
        return await self._call("fetch_val", query, *args)

    def transaction(self) -> Transaction:
        """Create an awaitable and async-context-manageable transaction."""
        return Transaction(self)
