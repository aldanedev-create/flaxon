"""Database backend implementation for session storage."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from flaxon.sessions.session import Session

# Allow standard SQL table identifiers (letters, numbers, underscores)
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
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id VARCHAR(64) PRIMARY KEY,
                data TEXT NOT NULL,
                ttl INTEGER NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )

    async def save(self, session: Session) -> None:
        """Save or update a session in the database."""
        await self.db.execute(
            f"""
            INSERT OR REPLACE INTO {self.table_name}
            (id, data, ttl, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session.id,
            json.dumps(session.to_dict(), default=str),
            session.ttl,
            session.created_at,
            session.created_at + session.ttl,
        )

    async def get(self, session_id: str) -> Session | None:
        """Fetch an active session by its ID."""
        row = await self.db.fetch_one(
            f"SELECT * FROM {self.table_name} WHERE id = $1 AND expires_at > $2",
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
            f"DELETE FROM {self.table_name} WHERE id = $1",
            session_id,
        )

    async def clear(self) -> None:
        """Remove all sessions from the database table."""
        await self.db.execute(f"DELETE FROM {self.table_name}")

    async def exists(self, session_id: str) -> bool:
        """Check if an active session exists."""
        row = await self.db.fetch_one(
            f"SELECT 1 FROM {self.table_name} WHERE id = $1 AND expires_at > $2",
            session_id,
            time.time(),
        )
        return row is not None

    async def cleanup(self) -> int:
        """Purge expired sessions from the database."""
        result = await self.db.execute(
            f"DELETE FROM {self.table_name} WHERE expires_at <= $1",
            time.time(),
        )
        return result if isinstance(result, int) else 0
