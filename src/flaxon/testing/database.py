from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Any

from flaxon.database.sql import statement


class DatabaseTestMixin:
    """Database test mixin implementation for the testing subsystem."""

    def __init__(self, db_manager: Any | None = None) -> None:
        self.db_manager = db_manager
        self._test_db_file: tempfile._TemporaryFileWrapper | None = None

    async def setup_database(self) -> None:
        """Perform the setup database operation for database test mixin."""
        if hasattr(self.db_manager, "pool"):
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as database_file:
                self._test_db_file = database_file
            os.environ["FLAXON_DATABASE_URL"] = f"sqlite:///{self._test_db_file.name}"

            if hasattr(self.db_manager, "initialize"):
                await self.db_manager.initialize()

    async def teardown_database(self) -> None:
        """Perform the teardown database operation for database test mixin."""
        if self._test_db_file:
            # FIX (SIM105): Replaced try...except OSError: pass with contextlib.suppress
            with contextlib.suppress(OSError):
                Path(self._test_db_file.name).unlink()
            self._test_db_file = None

    async def clear_database(self) -> None:
        """Clear the database."""
        if self.db_manager:
            tables = await self.db_manager.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            for table in tables:
                await self.db_manager.execute(statement("DELETE FROM {name_0}", name_0=table["name"]))

    async def transaction(self) -> Any:
        """Perform the transaction operation for database test mixin."""
        if self.db_manager:
            return await self.db_manager.transaction()
        return None
