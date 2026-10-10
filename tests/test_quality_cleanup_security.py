"""Regression checks for SQL composition and restricted task deserialization."""

import pickle
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from flaxon.database.sql import Assignments, Columns, Parameters, statement
from flaxon.tasks.serializer import Serializer


@pytest.mark.parametrize("name", ["users; DROP TABLE users", "users --", "users.name", "", "users\n"])
def test_sql_composition_rejects_unsafe_identifiers(name):
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        statement("SELECT * FROM {table}", table=name)
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        Columns(["id", name]).render()
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        Assignments([name]).render()


def test_sql_composition_keeps_values_out_of_statement():
    assert statement(
        "INSERT INTO {table} ({columns}) VALUES ({parameters})",
        table="projects", columns=Columns(["name", "owner_id"]), parameters=Parameters(2),
    ) == "INSERT INTO projects (name, owner_id) VALUES ($1, $2)"
    assert Assignments(["name", "owner_id"], start=3).render() == "name = $3, owner_id = $4"


class _ExecutablePayload:
    def __reduce__(self):
        return eval, ("1 + 2",)


def test_pickle_rejects_executable_globals_by_default():
    serializer = Serializer()
    payload = pickle.dumps(_ExecutablePayload())
    with pytest.raises(pickle.UnpicklingError, match="Unsupported pickle global"):
        serializer.from_pickle(payload)
    assert serializer.from_pickle(payload, trusted=True) == 3


def test_pickle_preserves_supported_values():
    serializer = Serializer()
    value = {"amount": Decimal("12.50"), "time": datetime(2026, 1, 1, tzinfo=UTC), "ids": {1, 2}}
    assert serializer.from_pickle(serializer.to_pickle(value)) == value


def test_synchronous_cache_writes_before_returning():
    from flaxon.caching.cache import Cache
    from flaxon.caching.decorators import cached

    calls = []

    @cached(cache=Cache())
    def calculate(value):
        calls.append(value)
        return value * 2

    assert calculate(3) == calculate(3) == 6
    assert calls == [3]


def test_lazy_import_supports_exported_values_and_child_modules():
    import json
    import xml.etree

    from flaxon._imports import import_attribute

    assert import_attribute("json", "loads") is json.loads
    assert import_attribute("xml", "etree") is xml.etree
    with pytest.raises(ImportError):
        import_attribute("json", "missing_flaxon_attribute")


def test_websocket_enum_preserves_string_representation():
    from flaxon.websocket.connection import WebSocketState

    assert str(WebSocketState.CONNECTED) == "WebSocketState.CONNECTED"
    assert WebSocketState.CONNECTED.value == "connected"
