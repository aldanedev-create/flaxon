"""Module mount isolation behavior and boundary cases."""

from flaxon import Flaxon
from flaxon.modules import FlaxonModule
from flaxon.testing import TestClient


def test_reusable_module_can_mount_under_distinct_app_prefixes():
    module = FlaxonModule("items")

    @module.get("/<int:item_id>")
    async def item(item_id):
        return {"id": item_id}

    first = Flaxon("first", debug=True)
    second = Flaxon("second", debug=True)
    first.mount_module(module, prefix="/first")
    second.mount_module(module, prefix="/second")
    assert TestClient(first).get("/first/1").json() == {"id": 1}
    assert TestClient(second).get("/second/2").json() == {"id": 2}
    assert TestClient(first).get("/second/2").status_code == 404
    assert module.router.routes[0].path == "/<int:item_id>"


def test_mount_preserves_http_methods(app, client):
    module = FlaxonModule("write")

    @module.post("/save")
    async def save():
        return {"saved": True}

    app.mount_module(module, prefix="/tools")
    assert client.post("/tools/save").json() == {"saved": True}
    assert client.get("/tools/save").status_code == 405
