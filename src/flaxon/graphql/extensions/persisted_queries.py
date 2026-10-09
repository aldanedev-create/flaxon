from __future__ import annotations

import hashlib
import json
from typing import Any

from flaxon.exceptions import BadRequest


class PersistedQueriesExtension:
    def __init__(self, storage: dict[str, str] | None = None, enabled: bool = True) -> None:
        self.storage = storage or {}
        self.enabled = enabled
        self._queries: dict[str, str] = {}

    def register(self, query_hash: str, query: str) -> None:
        self.storage[query_hash] = query
        self._queries[query_hash] = query

    def register_many(self, queries: dict[str, str]) -> None:
        self.storage.update(queries)
        self._queries.update(queries)

    def get(self, query_hash: str) -> str | None:
        return self.storage.get(query_hash)

    def get_auto_hash(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def resolve_persisted_query(self, query_hash: str, query_text: str | None = None) -> str | None:
        if query_text:
            return query_text

        return self.get(query_hash)

    def save_persisted_query(self, query_text: str) -> str:
        query_hash = self.get_auto_hash(query_text)
        self.register(query_hash, query_text)
        return query_hash

    def load_persisted_queries(self, file_path: str) -> None:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                self.register_many(data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_persisted_queries(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.storage, f, indent=2)

    async def before(self, context: dict[str, Any]) -> None:
        if not self.enabled:
            return

        request = context.get("request")
        if request is None:
            return

        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, BadRequest):
            return
        if not isinstance(data, dict):
            return

        query = data.get("query")
        extensions = data.get("extensions")
        if not isinstance(extensions, dict):
            return
        persisted = extensions.get("persistedQuery")
        if not isinstance(persisted, dict):
            return
        query_hash = persisted.get("sha256Hash")
        if not isinstance(query_hash, str):
            return

        if query_hash and not query:
            persisted_query = self.get(query_hash)
            if persisted_query:
                context["resolved_query"] = persisted_query

    async def after(self, context: dict[str, Any], result: dict[str, Any]) -> None:
        pass
