from __future__ import annotations

import re
from typing import Any, Generic, TypeVar

from .manager import DatabaseManager

T = TypeVar("T")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str, kind: str = "identifier") -> str:
    """Validate a string intended for use as a table/column name in a raw
    SQL string. Table and column names can't be parameterized as bind
    values (SQL doesn't support that), so this allowlist check is the
    real defense against SQL injection via identifiers -- without it,
    any caller-supplied column/table name (e.g. from Repository.find_by,
    or from the keys of a dict passed to create()/update()) would be
    interpolated into the query completely unescaped.
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid {kind} {name!r}: must match {_IDENTIFIER_RE.pattern} "
            f"(letters, digits, underscore, not starting with a digit)."
        )
    return name


class Repository(Generic[T]):
    def __init__(self, db: DatabaseManager, table_name: str) -> None:
        self.db = db
        self.table_name = _safe_identifier(table_name, "table name")

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        safe_keys = [_safe_identifier(k, "column name") for k in data.keys()]
        columns = ", ".join(safe_keys)
        placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
        return await self.db.fetch_one(query, *data.values())

    async def get(self, id: Any, id_column: str = "id") -> dict[str, Any] | None:
        id_column = _safe_identifier(id_column, "column name")
        query = f"SELECT * FROM {self.table_name} WHERE {id_column} = $1"
        return await self.db.fetch_one(query, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} LIMIT ${1} OFFSET ${2}"
        return await self.db.fetch_all(query, limit, offset)

    async def update(self, id: Any, data: dict[str, Any], id_column: str = "id") -> dict[str, Any] | None:
        id_column = _safe_identifier(id_column, "column name")
        set_clause = ", ".join(
            f"{_safe_identifier(key, 'column name')} = ${i+2}" for i, key in enumerate(data.keys())
        )
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {id_column} = $1 RETURNING *"
        return await self.db.fetch_one(query, id, *data.values())

    async def delete(self, id: Any, id_column: str = "id") -> bool:
        id_column = _safe_identifier(id_column, "column name")
        query = f"DELETE FROM {self.table_name} WHERE {id_column} = $1"
        result = await self.db.execute(query, id)
        return True

    async def count(self) -> int:
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        return await self.db.fetch_val(query)

    async def exists(self, id: Any, id_column: str = "id") -> bool:
        id_column = _safe_identifier(id_column, "column name")
        query = f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE {id_column} = $1)"
        return bool(await self.db.fetch_val(query, id))

    async def find_by(self, column: str, value: Any) -> list[dict[str, Any]]:
        column = _safe_identifier(column, "column name")
        query = f"SELECT * FROM {self.table_name} WHERE {column} = $1"
        return await self.db.fetch_all(query, value)

    async def find_one_by(self, column: str, value: Any) -> dict[str, Any] | None:
        column = _safe_identifier(column, "column name")
        query = f"SELECT * FROM {self.table_name} WHERE {column} = $1 LIMIT 1"
        return await self.db.fetch_one(query, value)

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not items:
            return []

        columns = [_safe_identifier(k, "column name") for k in items[0].keys()]
        column_str = ", ".join(columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))

        results = []
        for item in items:
            values = [item.get(col) for col in columns]
            query = f"INSERT INTO {self.table_name} ({column_str}) VALUES ({placeholders}) RETURNING *"
            result = await self.db.fetch_one(query, *values)
            results.append(result)

        return results

    async def bulk_update(self, items: list[dict[str, Any]], id_column: str = "id") -> list[dict[str, Any]]:
        id_column = _safe_identifier(id_column, "column name")
        results = []
        for item in items:
            id_value = item.get(id_column)
            if id_value is None:
                continue
            data = {k: v for k, v in item.items() if k != id_column}
            result = await self.update(id_value, data, id_column)
            results.append(result)
        return results

    async def delete_all(self) -> int:
        query = f"DELETE FROM {self.table_name}"
        result = await self.db.execute(query)
        return 0

    async def paginate(self, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        offset = (page - 1) * per_page
        items = await self.get_all(per_page, offset)
        total = await self.count()
        total_pages = (total + per_page - 1) // per_page

        return {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
