"""Database backend implementation for session storage."""

from __future__ import annotations

import json
import re
import time
from typing import Any

# Allow standard SQL table identifiers (letters, numbers, underscores)
from flaxon.database.sql import statement
from flaxon.sessions.session import Session

_TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class DatabaseBackend:
    """Database-backed session storage handler."""

    def __init__(
        self,
        db_manager: Any,
        table_name: str = "sessions",
    ) -> None:
        if not _TABLE_NAME_PATTERN.match(table_name):
            raise ValueError(f"Invalid table name identifier: {table_name!r}")

        self.db = db_manager
        self.table_name = table_name

    async def initialize(self) -> None:
        """Create the sessions table if it does not already exist."""
        await self.db.execute(
            statement(
                (
                    "\n            CREATE TABLE IF NOT EXISTS {name_0} (\n         "
                    "       id VARCHAR(64) PRIMARY KEY,\n                data TEXT"
                    " NOT NULL,\n                ttl INTEGER NOT NULL,\n           "
                    "     created_at REAL NOT NULL,\n                expires_at RE"
                    "AL NOT NULL\n            )\n            "
                ),
                name_0=self.table_name,
            )
        )

    async def save(self, session: Session) -> None:
        """Save or update a session in the database."""
        await self.db.execute(
            statement(
                (
                    "\n            INSERT OR REPLACE INTO {name_0}\n            (id"
                    ", data, ttl, created_at, expires_at)\n            VALUES ($1,"
                    " $2, $3, $4, $5)\n            "
                ),
                name_0=self.table_name,
            ),
            session.id,
            json.dumps(session.to_dict(), default=str),
            session.ttl,
            session.created_at,
            session.created_at + session.ttl,
        )

    async def get(self, session_id: str) -> Session | None:
        """Fetch an active session by its ID."""
        row = await self.db.fetch_one(
            statement("SELECT * FROM {name_0} WHERE id = $1 AND expires_at > $2", name_0=self.table_name),
            session_id,
            time.time(),
        )

        if row is None:
            return None

        data = json.loads(row["data"])
        return Session(
            session_id=row["id"],
            data=data.get("data", {}),
            ttl=row["ttl"],
            created_at=row["created_at"],
        )

    async def delete(self, session_id: str) -> None:
        """Delete a specific session by its ID."""
        await self.db.execute(
            statement("DELETE FROM {name_0} WHERE id = $1", name_0=self.table_name),
            session_id,
        )

    async def clear(self) -> None:
        """Remove all sessions from the database table."""
        await self.db.execute(statement("DELETE FROM {name_0}", name_0=self.table_name))

    async def exists(self, session_id: str) -> bool:
        """Check if an active session exists."""
        row = await self.db.fetch_one(
            statement("SELECT 1 FROM {name_0} WHERE id = $1 AND expires_at > $2", name_0=self.table_name),
            session_id,
            time.time(),
        )
        return row is not None

    async def cleanup(self) -> int:
        """Purge expired sessions from the database."""
        result = await self.db.execute(
            statement("DELETE FROM {name_0} WHERE expires_at <= $1", name_0=self.table_name),
            time.time(),
        )
        return result if isinstance(result, int) else 0
