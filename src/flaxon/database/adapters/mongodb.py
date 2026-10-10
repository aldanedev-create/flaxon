from __future__ import annotations

from typing import Any

from flaxon._imports import import_attribute

from .base import BaseAdapter


class MongoDBAdapter(BaseAdapter):
    """Mongo dbadapter implementation for the database subsystem."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        database: str = "test",
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.kwargs = kwargs
        self._client = None
        self._db = None

    async def connect(self) -> None:
        """Open the configured connection."""
        try:
            async_iomotor_client_type = import_attribute("motor.motor_asyncio", "AsyncIOMotorClient")

            uri = f"mongodb://{self.host}:{self.port}"
            if self.username and self.password:
                uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}"

            self._client = async_iomotor_client_type(uri, **self.kwargs)
            self._db = self._client[self.database]
        except ImportError as exc:
            raise RuntimeError("motor is required for MongoDB. Install with: pip install motor") from exc

    async def disconnect(self) -> None:
        """Close the configured connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute the supplied operation with its parameters."""
        raise NotImplementedError("MongoDB does not support SQL queries")

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch the one."""
        raise NotImplementedError("MongoDB does not support SQL queries")

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch the all."""
        raise NotImplementedError("MongoDB does not support SQL queries")

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """Fetch the val."""
        raise NotImplementedError("MongoDB does not support SQL queries")

    async def find_one(self, collection: str, filter: dict[str, Any]) -> dict[str, Any] | None:
        """Find the one."""
        result = await self._db[collection].find_one(filter)
        if result:
            result["_id"] = str(result["_id"])
        return result

    async def find_many(self, collection: str, filter: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]:
        """Find the many."""
        cursor = self._db[collection].find(filter, **kwargs)
        results = await cursor.to_list(length=kwargs.get("limit", 100))
        for result in results:
            result["_id"] = str(result["_id"])
        return results

    async def insert_one(self, collection: str, document: dict[str, Any]) -> str:
        """Perform the insert one operation for mongo dbadapter."""
        result = await self._db[collection].insert_one(document)
        return str(result.inserted_id)

    async def insert_many(self, collection: str, documents: list[dict[str, Any]]) -> list[str]:
        """Perform the insert many operation for mongo dbadapter."""
        result = await self._db[collection].insert_many(documents)
        return [str(id) for id in result.inserted_ids]

    async def update_one(self, collection: str, filter: dict[str, Any], update: dict[str, Any]) -> int:
        """Update the one."""
        result = await self._db[collection].update_one(filter, update)
        return result.modified_count

    async def update_many(self, collection: str, filter: dict[str, Any], update: dict[str, Any]) -> int:
        """Update the many."""
        result = await self._db[collection].update_many(filter, update)
        return result.modified_count

    async def delete_one(self, collection: str, filter: dict[str, Any]) -> int:
        """Delete the one."""
        result = await self._db[collection].delete_one(filter)
        return result.deleted_count

    async def delete_many(self, collection: str, filter: dict[str, Any]) -> int:
        """Delete the many."""
        result = await self._db[collection].delete_many(filter)
        return result.deleted_count

    async def count(self, collection: str, filter: dict[str, Any] | None = None) -> int:
        """Return the number of matching entries."""
        return await self._db[collection].count_documents(filter or {})

    async def begin(self) -> None:
        """Perform the begin operation for mongo dbadapter."""
        if self._client:
            async with await self._client.start_session() as session:
                session.start_transaction()
                self._session = session

    async def commit(self) -> None:
        """Perform the commit operation for mongo dbadapter."""
        if hasattr(self, "_session"):
            await self._session.commit_transaction()
            self._session = None

    async def rollback(self) -> None:
        """Perform the rollback operation for mongo dbadapter."""
        if hasattr(self, "_session"):
            await self._session.abort_transaction()
            self._session = None

    async def ping(self) -> bool:
        """Perform the ping operation for mongo dbadapter."""
        try:
            await self._db.command("ping")
            return True
        except Exception:
            return False
