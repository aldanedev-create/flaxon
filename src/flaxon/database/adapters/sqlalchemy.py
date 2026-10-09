from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class SQLAlchemyAdapter(BaseAdapter):
    def __init__(self, database_url: str, **kwargs: Any) -> None:
        self.database_url = database_url
        self.kwargs = kwargs
        self._engine = None
        self._session = None

    @staticmethod
    def _prepare(query: str, args: tuple[Any, ...]) -> tuple[Any, dict[str, Any]]:
        """Use named binds so the adapter accepts the same positional style as SQL adapters."""
        import re

        from sqlalchemy import text

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
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            from sqlalchemy.orm import sessionmaker

            self._engine = create_async_engine(self.database_url, **self.kwargs)
            self._sessionmaker = sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)
        except ImportError as exc:
            raise RuntimeError(
                "sqlalchemy is required. Install with: pip install sqlalchemy[asyncio]"
            ) from exc

    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session = None

    async def execute(self, query: str, *args: Any) -> Any:
        session = self._session or self._sessionmaker()
        context = session if self._session else session
        async with context:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            await session.commit()
            return result

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        async with self._sessionmaker() as session:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            row = result.first()
            if row is None:
                return None
            return dict(row._mapping)

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        async with self._sessionmaker() as session:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            return [dict(row._mapping) for row in result.all()]

    async def fetch_val(self, query: str, *args: Any) -> Any:
        async with self._sessionmaker() as session:
            statement, params = self._prepare(query, args)
            result = await session.execute(statement, params)
            row = result.first()
            return row[0] if row else None

    async def begin(self) -> None:
        self._session = self._sessionmaker()

    async def commit(self) -> None:
        if self._session:
            await self._session.commit()
            self._session = None

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()
            self._session = None

    async def ping(self) -> bool:
        try:
            from sqlalchemy import text

            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @property
    def session(self) -> Any:
        return self._session
