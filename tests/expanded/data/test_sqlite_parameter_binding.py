"""Sqlite parameter binding behavior and boundary cases."""

import pytest

from flaxon.database.adapters.sqlite import SQLiteAdapter


@pytest.mark.asyncio
async def test_bound_values_cannot_change_query_structure():
    db = SQLiteAdapter()
    await db.connect()
    try:
        await db.execute("CREATE TABLE notes (body TEXT)")
        payload = "'); DROP TABLE notes; --"
        await db.execute("INSERT INTO notes (body) VALUES ($1)", payload)
        assert await db.fetch_one("SELECT body FROM notes") == {"body": payload}
        assert await db.fetch_val("SELECT COUNT(*) FROM notes") == 1
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_repeated_and_reordered_parameters_are_bound():
    db = SQLiteAdapter()
    await db.connect()
    try:
        assert await db.fetch_one("SELECT $2 AS second, $1 AS first, $2 AS repeated", "a", "b") == {
            "second": "b",
            "first": "a",
            "repeated": "b",
        }
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_missing_row_defaults_are_consistent():
    db = SQLiteAdapter()
    await db.connect()
    try:
        assert await db.fetch_one("SELECT 1 WHERE 0") is None
        assert await db.fetch_all("SELECT 1 WHERE 0") == []
        assert await db.fetch_val("SELECT 1 WHERE 0") is None
    finally:
        await db.disconnect()
