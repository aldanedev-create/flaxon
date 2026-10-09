from __future__ import annotations

import contextlib
import os
import tempfile
from typing import Any


class DatabaseTestMixin:

    def __init__(self, db_manager: Any | None = None) -> None:
        self.db_manager = db_manager
        self._test_db_file: tempfile._TemporaryFileWrapper | None = None

    async def setup_database(self) -> None:
        if hasattr(self.db_manager, "pool"):
            self._test_db_file = tempfile.NamedTemporaryFile(
                suffix=".db", delete=False
            )
            self._test_db_file.close()
            os.environ["FLAXON_DATABASE_URL"] = (
                f"sqlite:///{self._test_db_file.name}"
            )

            if hasattr(self.db_manager, "initialize"):
                await self.db_manager.initialize()

    async def teardown_database(self) -> None:
        if self._test_db_file:
            # FIX (SIM105): Replaced try...except OSError: pass with contextlib.suppress
            with contextlib.suppress(OSError):
                os.unlink(self._test_db_file.name)
            self._test_db_file = None

    async def clear_database(self) -> None:
        if self.db_manager:
            tables = await self.db_manager.fetch_all(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            for table in tables:
                await self.db_manager.execute(f"DELETE FROM {table['name']}")

    async def transaction(self) -> Any:
        if self.db_manager:
            return await self.db_manager.transaction()
        return None
