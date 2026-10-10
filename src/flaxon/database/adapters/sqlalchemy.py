from __future__ import annotations

import re
from typing import Any

from flaxon._imports import import_attribute

from .base import BaseAdapter


class SQLAlchemyAdapter(BaseAdapter):
    """Sqlalchemy adapter implementation for the database subsystem."""

    def __init__(self, database_url: str, **kwargs: Any) -> None:
        self.database_url = database_url
        self.kwargs = kwargs
        self._engine = None
        self._session = None

    @staticmethod
    def _prepare(query: str, args: tuple[Any, ...]) -> tuple[Any, dict[str, Any]]:
        """Use named binds so the adapter accepts the same positional style as SQL adapters."""
        text = import_attribute("sqlalchemy", "text")

        names: list[str] = []

        def replace(match: Any) -> str:
            name = f"p{len(names) + 1}"
            names.append(name)
            return f":{name}"

        query = re.sub(r"\$(\d+)", replace, query)
        if not names and "?" in query:
            query = re.sub(r"\?", replace, query)
        return text(query), {name: args[index] for index, name in enumerate(names)}

    async def connect(self) -> None:
        """Open the configured connection."""
        try:
            async_session_type = import_attribute("sqlalchemy.ext.asyncio", "AsyncSession")
            create_async_engine = import_attribute("sqlalchemy.ext.asyncio", "create_async_engine")
            sessionmaker = import_attribute("sqlalchemy.orm", "sessionmaker")

            self._engine = create_async_engine(self.database_url, **self.kwargs)
            self._sessionmaker = sessionmaker(self._engine, class_=async_session_type, expire_on_commit=False)
        except ImportError as exc:
            raise RuntimeError(
                "sqlalchemy is required. Install with: pip install sqlalchemy[asyncio]"
            ) from exc

    async def disconnect(self) -> None:
        """Close the configured connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session = None

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        session = self._session or self._sessionmaker()
        context = session
        async with context:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            await session.commit()
            return result

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        async with self._sessionmaker() as session:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            row = result.first()
            if row is None:
                return None
            return dict(row._mapping)

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        async with self._sessionmaker() as session:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            return [dict(row._mapping) for row in result.all()]

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        async with self._sessionmaker() as session:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            row = result.first()
            return row[0] if row else None

    async def begin(self) -> None:
        """Perform the begin operation for sqlalchemy adapter."""
        self._session = self._sessionmaker()

    async def commit(self) -> None:
        """Perform the commit operation for sqlalchemy adapter."""
        if self._session:
            await self._session.commit()
            self._session = None

    async def rollback(self) -> None:
        """Perform the rollback operation for sqlalchemy adapter."""
        if self._session:
            await self._session.rollback()
            self._session = None

    async def ping(self) -> bool:
        """Perform the ping operation for sqlalchemy adapter."""
        try:
            text = import_attribute("sqlalchemy", "text")

            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @property
    def session(self) -> Any:
        """Return the configured session."""
        return self._session
