"""Transaction helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextvars import Token
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .manager import DatabaseManager


class Transaction:
    """An awaitable transaction that also supports ``async with``."""

    def __init__(self, manager: DatabaseManager) -> None:
        self.manager = manager
        self.depth = 0
        self._active = False
        self._connection: Any = None
        self._owns_connection = False
        self._connection_token: Token[Any | None] | None = None
        self._depth_token: Token[int] | None = None

    def __await__(self) -> Generator[Any, None, Transaction]:
        return self._prepare().__await__()

    async def _prepare(self) -> Transaction:
        if not self.manager._direct and self._connection is None:
            active_connection = self.manager._transaction_connection.get()
            if active_connection is None:
                self._connection = await self.manager.pool.acquire()
                self._owns_connection = True
                self._connection_token = self.manager._transaction_connection.set(self._connection)
            else:
                # Nested transactions must use the outer transaction's
                # connection so their savepoints have the intended scope.
                self._connection = active_connection
        return self

    async def __aenter__(self) -> Transaction:
        await self.begin()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            if self._active:
                self._reset_depth()
                self._active = False
            await self.close()

    async def begin(self) -> None:
        """Perform the begin operation for transaction."""
        await self._prepare()
        self.depth = self.manager._transaction_depth.get()
        self._depth_token = self.manager._transaction_depth.set(self.depth + 1)
        try:
            if self.depth == 0:
                target = self.manager.pool if self.manager._direct else self._connection
                if hasattr(target, "begin"):
                    await target.begin()
                else:
                    await target.execute("BEGIN")
            else:
                await self._execute_raw(f"SAVEPOINT flaxon_tx_{self.depth}")
        except Exception:
            self._reset_depth()
            await self.close()
            raise
        self._active = True

    async def commit(self) -> None:
        """Perform the commit operation for transaction."""
        if not self._active:
            return
        if self.depth == 0:
            target = self.manager.pool if self.manager._direct else self._connection
            if hasattr(target, "commit"):
                await target.commit()
            else:
                await target.execute("COMMIT")
        else:
            await self._execute_raw(f"RELEASE SAVEPOINT flaxon_tx_{self.depth}")
        self._reset_depth()
        self._active = False

    async def rollback(self) -> None:
        """Perform the rollback operation for transaction."""
        if not self._active:
            return
        if self.depth == 0:
            target = self.manager.pool if self.manager._direct else self._connection
            if hasattr(target, "rollback"):
                await target.rollback()
            else:
                await target.execute("ROLLBACK")
        else:
            await self._execute_raw(f"ROLLBACK TO SAVEPOINT flaxon_tx_{self.depth}")
        self._reset_depth()
        self._active = False

    async def close(self) -> None:
        """Release the resources held by this object."""
        if self._owns_connection and self._connection is not None:
            await self.manager.pool.release(self._connection)
        if self._connection_token is not None:
            self.manager._transaction_connection.reset(self._connection_token)
            self._connection_token = None
        if self._owns_connection:
            self._connection = None
            self._owns_connection = False

    def _reset_depth(self) -> None:
        if self._depth_token is not None:
            self.manager._transaction_depth.reset(self._depth_token)
            self._depth_token = None

    async def _execute_raw(self, query: str, *args: Any) -> Any:
        """Perform the  execute raw operation for transaction."""
        target = self.manager.pool if self.manager._direct else self._connection
        return await target.execute(query, *args)

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        if not self._active:
            raise RuntimeError("Transaction not active")
        return await self._execute_raw(query, *args)


def transaction(func: Any) -> Any:
    """Inject a transaction into an async instance method."""

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        async with self._db.transaction() as current:
            kwargs["transaction"] = current
            return await func(self, *args, **kwargs)

    return wrapper
