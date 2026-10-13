import logging

import pytest

from flaxon import Flaxon, Router
from flaxon.admin import AdminDashboard
from flaxon.admin.cms import CMS


def test_admin_and_cms_match_in_either_registration_order(caplog):
    caplog.set_level(logging.WARNING, logger="flaxon.routing.router")
    for cms_first in (False, True):
        app = Flaxon(f"route-order-{cms_first}")
        if cms_first:
            CMS(app)
            AdminDashboard(app, users=[{"username": "admin", "password": "Admin123!"}])
        else:
            AdminDashboard(app, users=[{"username": "admin", "password": "Admin123!"}])
            CMS(app)

        match = app.router.match("/admin/cms/", "GET")
        assert match.route.endpoint.__name__ == "spa"
        api_match = app.router.match("/admin/cms/api/config", "GET")
        assert api_match.route.endpoint.__name__ == "api_config"
    assert not [record for record in caplog.records if record.name == "flaxon.routing.router"]


def test_include_router_applies_mount_prefix_without_mutating_source():
    source = Router(prefix="/api")

    @source.get("/items/<int:item_id>")
    async def item(request, item_id):
        return {"id": item_id}

    destination = Router()
    destination.include_router(source, prefix="/v1")

    assert destination.match("/v1/items/42", "GET").params == {"item_id": 42}
    assert source.match("/api/items/42", "GET").params == {"item_id": 42}


def test_include_router_applies_mount_prefix_to_websocket_routes():
    source = Router(prefix="/api")

    @source.websocket("/events/<room_id>")
    async def events(socket, room_id):
        return room_id

    destination = Router()
    destination.include_router(source, prefix="/v1")

    match = destination.match_websocket("/v1/events/general")
    assert match.params == {"room_id": "general"}
    assert source.match_websocket("/api/events/general").params == {"room_id": "general"}


def test_expected_overlap_is_debug_and_non_overlapping_routes_are_silent(caplog):
    router = Router()
    caplog.set_level(logging.DEBUG, logger="flaxon.routing.router")

    @router.get("/admin/<model_name>")
    async def model(request, model_name):
        return model_name

    @router.get("/admin/cms")
    async def cms(request):
        return "cms"

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.DEBUG
    assert "specificity will decide" in caplog.records[0].message
    caplog.clear()

    @router.get("/settings")
    async def settings(request):
        return "settings"

    assert not caplog.records
    assert router.match("/admin/cms", "GET").route.endpoint.__name__ == "cms"


@pytest.mark.parametrize("reverse", [False, True])
def test_expected_admin_overlap_never_warns_in_either_order(caplog, reverse):
    router = Router()
    caplog.set_level(logging.WARNING, logger="flaxon.routing.router")

    async def model(request, model_name):
        return model_name

    async def users(request):
        return "users"

    entries = [("/admin/<model_name>", model), ("/admin/users", users)]
    for path, endpoint in reversed(entries) if reverse else entries:
        router.get(path)(endpoint)
    assert not caplog.records
    assert router.match("/admin/users", "GET").route.endpoint is users
    assert router.match("/admin/products", "GET").route.endpoint is model


@pytest.mark.parametrize("paths", [
    ("/users", "/users"),
    ("/users/<id>", "/users/<name>"),
    ("/users/<id>", "/users/<id>"),
])
def test_ambiguous_routes_warn_and_keep_first_registration(caplog, paths):
    router = Router()
    caplog.set_level(logging.WARNING, logger="flaxon.routing.router")

    async def first(request, **params):
        return "first"

    async def second(request, **params):
        return "second"

    router.get(paths[0])(first)
    router.get(paths[1])(second)
    assert len(caplog.records) == 1
    assert "Ambiguous route collision" in caplog.records[0].message
    assert "registration order will decide" in caplog.records[0].message
    path = "/users/123" if "<" in paths[0] else "/users"
    assert router.match(path, "GET").route.endpoint is first


def test_distinct_methods_and_slash_paths_do_not_warn(caplog):
    router = Router()
    caplog.set_level(logging.DEBUG, logger="flaxon.routing.router")

    async def endpoint(request, **params):
        return "ok"

    router.get("/admin/cms")(endpoint)
    router.get("/admin/cms/")(endpoint)
    router.post("/admin/cms")(endpoint)
    router.get("/items/<int:id>")(endpoint)
    router.get("/items/new")(endpoint)
    assert not caplog.records


def test_included_router_reports_ambiguous_dynamic_routes(caplog):
    source, destination = Router(), Router()
    caplog.set_level(logging.WARNING, logger="flaxon.routing.router")

    async def endpoint(request, **params):
        return "ok"

    destination.get("/api/<id>")(endpoint)
    source.get("/<name>")(endpoint)
    destination.include_router(source, prefix="/api")
    assert len(caplog.records) == 1
    assert "Ambiguous route collision" in caplog.records[0].message
