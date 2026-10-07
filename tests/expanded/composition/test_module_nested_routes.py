"""Module nested routes behavior and boundary cases."""

import pytest

from flaxon.modules import FlaxonModule, ModuleCycleError


def test_nested_mount_combines_prefixes(app, client):
    parent = FlaxonModule("parent")
    child = FlaxonModule("child")

    @child.get("/items")
    async def items():
        return {"nested": True}

    parent.register_module(child, prefix="/child")
    app.mount_module(parent, prefix="/api")
    assert client.get("/api/child/items").json() == {"nested": True}
    assert client.get("/child/items").status_code == 404


def test_direct_cycle_is_rejected():
    module = FlaxonModule("cycle")
    with pytest.raises(ModuleCycleError):
        module.register_module(module)


def test_indirect_cycle_is_rejected():
    parent = FlaxonModule("parent")
    child = FlaxonModule("child")
    parent.register_module(child)
    with pytest.raises(ModuleCycleError):
        child.register_module(parent)
