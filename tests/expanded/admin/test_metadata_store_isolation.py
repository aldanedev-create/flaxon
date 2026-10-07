"""Metadata store isolation behavior and boundary cases."""

import pytest

from flaxon.admin.services import AdminStore


def test_namespaces_isolate_equal_keys(admin_store):
    admin_store.set("users", "same", {"role": "staff"})
    admin_store.set("settings", "same", {"theme": "dark"})
    assert admin_store.get("users", "same") == {"role": "staff"}
    assert admin_store.get("settings", "same") == {"theme": "dark"}


def test_store_survives_reopening(admin_store):
    admin_store.set("users", "name", {"unicode": "日本"})
    assert AdminStore(admin_store.path).get("users", "name") == {"unicode": "日本"}


def test_failed_mutation_rolls_back(admin_store):
    admin_store.set("settings", "value", {"count": 1})

    def fail(value):
        value["count"] = 99
        raise RuntimeError("abort")

    with pytest.raises(RuntimeError):
        admin_store.mutate("settings", "value", fail)
    assert admin_store.get("settings", "value") == {"count": 1}
