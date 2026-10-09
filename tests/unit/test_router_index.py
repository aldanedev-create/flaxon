"""Indexed routing must preserve the previous ordered matching contract."""

import itertools
import uuid

import pytest

from flaxon.exceptions import MethodNotAllowed, NotFound
from flaxon.routing.converters import CONVERTERS, Converter
from flaxon.routing.route import Route
from flaxon.routing.router import Router


def endpoint(**kwargs):
    return kwargs


def reference_match(router, path, method):
    for route in router.routes:
        if not route.parameters and route.path == path and method in route.methods:
            return route, {}
    matched_path = False
    for route in sorted(router.routes, key=router._priority):
        params = route.match(path)
        if params is not None:
            matched_path = True
            if method in route.methods:
                return route, params
    raise MethodNotAllowed() if matched_path else NotFound()


def outcome(match):
    try:
        return match()
    except (NotFound, MethodNotAllowed) as exc:
        return type(exc)


def test_index_matches_ordered_reference_for_converters_and_methods(monkeypatch):
    monkeypatch.setitem(CONVERTERS, "nested", Converter(r"[^/]+/[^/]+", str))
    router = Router()
    paths = [
        "/",
        "/api/items/new",
        "/api/items/<int:object_id>",
        "/api/items/<slug:slug>",
        "/api/<path:rest>",
        "/<path:everything>",
        "/api/items/<int:object_id>/children/<uuid:child>",
        "/api/files/file-<slug:name>.json",
        "/v<int:version>/items/<str:item>",
        "/api/files/<nested:name>/metadata",
        "/api/items/<float:amount>/",
        "/api//items/<int:object_id>",
        "/api/items/<int:object_id>/edit",
    ]
    for index, path in enumerate(paths):
        router.route(path, methods={"GET" if index % 2 else "POST"})(endpoint)
    child_id = str(uuid.uuid4())
    requests = [
        "/",
        "/api/items/new",
        "/api/items/42",
        "/api/items/-42",
        "/api/items/slug",
        "/api/items/42/",
        "/api/items/3.5/",
        "/api/files/file-notes.json",
        "/api/files/folder/file/metadata",
        f"/api/items/42/children/{child_id}",
        "/api/items/42/children/not-a-uuid",
        "/v2/items/book",
        "/api//items/42",
        "/api/items/42/edit",
        "/missing/thing",
        "/api/items/",
        "",
        "api/items/42",
    ]
    for path, method in itertools.product(requests, ["GET", "POST", "DELETE"]):
        expected = outcome(lambda: reference_match(router, path, method))

        def indexed():
            match = router.match(path, method.lower())
            return match.route, match.params

        assert outcome(indexed) == expected, (path, method)


def test_dynamic_index_avoids_unrelated_common_prefix_routes(monkeypatch):
    router = Router()
    for number in range(1000):
        router.get(f"/api/resource{number}/<int:object_id>")(endpoint)
    calls = []
    original = Route.match

    def counted(route, path):
        calls.append(route.path)
        return original(route, path)

    monkeypatch.setattr(Route, "match", counted)
    assert router.match("/api/resource999/42", "GET").params == {"object_id": 42}
    assert calls == ["/api/resource999/<int:object_id>"]
    calls.clear()
    with pytest.raises(NotFound):
        router.match("/api/unknown/42", "GET")
    assert not calls


def test_registration_and_mounts_are_visible_after_a_previous_lookup():
    router = Router()
    router.get("/api/<path:rest>")(endpoint)
    assert router.match("/api/items/42", "GET").params == {"rest": "items/42"}
    source = Router(prefix="/source")
    source.get("/items/<int:object_id>", name="specific")(endpoint)
    router.include_router(source, prefix="/api")
    assert router.match("/api/items/42", "GET").route.name == "specific"
    assert source.match("/source/items/42", "GET").params == {"object_id": 42}
    router.get("/api/items/42", name="exact")(endpoint)
    assert router.match("/api/items/42", "GET").route.name == "exact"


def test_equal_priority_registration_order_and_method_fallback():
    router = Router()
    router.post("/api/items/new")(endpoint)
    router.get("/api/items/<slug:first>", name="first")(endpoint)
    router.get("/api/items/<str:second>", name="second")(endpoint)
    assert router.match("/api/items/new", "GET").route.name == "first"
    with pytest.raises(MethodNotAllowed):
        router.match("/api/items/new", "DELETE")
    assert router.match("/api/items/anything", "GET").route.name == "first"
