"""Module hook boundaries behavior and boundary cases."""

from flaxon.exceptions import Forbidden
from flaxon.modules import FlaxonModule


def test_hooks_run_in_order_and_do_not_wrap_unrelated_routes(app, client):
    events = []
    module = FlaxonModule("hooked")

    @module.before_request
    async def before(request):
        events.append("before")

    @module.after_request
    def after(request, result):
        events.append("after")
        assert result == {"id": 7}

    @module.get("/<int:item_id>")
    async def item(item_id):
        events.append("handler")
        return {"id": item_id}

    @app.get("/other")
    async def other():
        return {"other": True}

    app.mount_module(module, prefix="/items")
    assert client.get("/other").status_code == 200
    assert events == []
    assert client.get("/items/7").json() == {"id": 7}
    assert events == ["before", "handler", "after"]


def test_before_hook_can_block_handler(app, client):
    called = []
    module = FlaxonModule("blocked")

    @module.before_request
    def guard(request):
        raise Forbidden("blocked")

    @module.get("/")
    async def endpoint():
        called.append(True)
        return "secret"

    app.mount_module(module, prefix="/blocked")
    assert client.get("/blocked/").status_code == 403
    assert called == []


def test_module_error_handler_transforms_owned_failure(app, client):
    module = FlaxonModule("errors")

    @module.errorhandler(ValueError)
    def handle(request, error):
        return {"error": str(error)}

    @module.get("/")
    async def endpoint():
        raise ValueError("bad value")

    app.mount_module(module, prefix="/errors")
    assert client.get("/errors/").json() == {"error": "bad value"}
