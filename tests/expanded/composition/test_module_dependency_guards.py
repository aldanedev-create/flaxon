"""Module dependency guards behavior and boundary cases."""

import pytest

from flaxon.modules import FlaxonModule, ModuleAlreadyMountedError, ModuleDependencyError


def test_missing_dependency_fails_before_routes_are_added(app, client):
    module = FlaxonModule("dependent")
    module.requires("catalog")

    @module.get("/items")
    async def items():
        return []

    with pytest.raises(ModuleDependencyError, match="catalog"):
        app.mount_module(module, prefix="/api")
    assert client.get("/api/items").status_code == 404


def test_registered_dependency_is_injected_into_module_handler(app, client):
    module = FlaxonModule("dependent")
    module.requires("catalog")
    app.container.register_instance("catalog", {"count": 3})

    @module.get("/count")
    async def count(catalog):
        return catalog

    app.mount_module(module, prefix="/api")
    assert client.get("/api/count").json() == {"count": 3}


def test_duplicate_mount_is_rejected(app):
    module = FlaxonModule("same")
    app.mount_module(module, prefix="/first")
    with pytest.raises(ModuleAlreadyMountedError):
        app.mount_module(module, prefix="/second")
