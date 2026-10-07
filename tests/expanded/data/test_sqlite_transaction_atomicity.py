"""Sqlite transaction atomicity behavior and boundary cases."""

import pytest

from flaxon.database.adapters.sqlite import SQLiteAdapter
from flaxon.database.manager import DatabaseManager


@pytest.mark.asyncio
async def test_failed_transaction_rolls_back_all_writes():
    db = DatabaseManager(SQLiteAdapter())
    await db.initialize()
    try:
        await db.execute("CREATE TABLE items (id INTEGER)")
        with pytest.raises(RuntimeError):
            async with db.transaction() as tx:
                await tx.execute("INSERT INTO items VALUES (1)")
                await db.execute("INSERT INTO items VALUES (2)")
                raise RuntimeError("cancel")
        assert await db.fetch_val("SELECT COUNT(*) FROM items") == 0
        async with db.transaction() as tx:
            await tx.execute("INSERT INTO items VALUES (3)")
        assert await db.fetch_val("SELECT id FROM items") == 3
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_nested_failure_only_rolls_back_savepoint():
    db = DatabaseManager(SQLiteAdapter())
    await db.initialize()
    try:
        await db.execute("CREATE TABLE items (id INTEGER)")
        async with db.transaction() as outer:
            await outer.execute("INSERT INTO items VALUES (1)")
            with pytest.raises(ValueError):
                async with db.transaction() as inner:
                    await inner.execute("INSERT INTO items VALUES (2)")
                    raise ValueError("inner")
            await outer.execute("INSERT INTO items VALUES (3)")
        assert await db.fetch_all("SELECT id FROM items ORDER BY id") == [{"id": 1}, {"id": 3}]
    finally:
        await db.close()
