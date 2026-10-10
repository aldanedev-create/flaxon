"""SSR integration and development diagnostic trust boundaries."""

import json

import pytest

from flaxon import Flaxon, Request
from flaxon.testing import TestClient


def application(tmp_path, *, debug=True, source=None, fallback="error"):
    (tmp_path / "ui").mkdir(exist_ok=True)
    (tmp_path / "ui/app.html").write_text(
        source or "<template><article><h1>{{ title }}</h1></article></template>"
    )
    app = Flaxon("SSR", debug=debug)
    app.use_teloce(
        project_root=tmp_path, options={"ssr": "opt-in", "ssr_fallback": fallback, "bundle": False}
    )

    @app.get("/")
    async def index(request: Request):
        return await request.compile(
            "app.html",
            {"title": "<Hello>"},
            ssr=True,
            meta={
                "title": "Public page",
                "description": 'Safe "description"',
                "canonical": "https://example.com/",
            },
        )

    return app, TestClient(app)


def test_ssr_contains_public_html_metadata_and_hydration(tmp_path):
    app, client = application(tmp_path)
    response = client.get("/")
    assert response.status_code == 200, response.text
    assert "<h1>&lt;Hello&gt;</h1>" in response.text
    assert 'data-teloce-ssr="1"' in response.text
    assert 'hydrate("#app", context)' in response.text
    assert "<title>Public page</title>" in response.text
    assert 'rel="canonical"' in response.text
    assert "flaxon-debug.js" in response.text


def test_browser_report_is_bounded_escaped_and_visible(tmp_path):
    app, client = application(tmp_path)
    client.get("/")
    headers = {"origin": "http://testserver", "x-flaxon-debug-token": app.teloce.debugger.token}
    payload = {
        "category": "runtime",
        "component": "ui/app.html",
        "line": 1,
        "message": "<script>danger()</script>",
        "stack": "<img src=x onerror=bad()>",
        "path": "/page?token=secret",
    }
    response = client.post("/__debug__/teloce/errors", json_data=payload, headers=headers)
    assert response.status_code == 200, response.text
    error = app.error_store.get(response.json()["error_id"])
    assert error["client_reported"] is True and error["path"] == "/page"
    assert error["location"].startswith("ui/app.html:1:")
    dashboard = client.get("/__debug__").text
    assert "<script>danger()" not in dashboard
    assert "&lt;script&gt;danger()" in dashboard
    assert "ui/app.html:1:" in dashboard
    assert client.post("/__debug__/teloce/errors", json_data=payload).status_code == 403
    assert (
        client.post(
            "/__debug__/teloce/errors",
            json_data=payload,
            headers={**headers, "origin": "https://evil.example"},
        ).status_code
        == 403
    )
    oversized = {**payload, "stack": "x" * 40000}
    assert client.post("/__debug__/teloce/errors", json_data=oversized, headers=headers).status_code == 400


def test_production_has_no_debug_client_endpoint_or_asset(tmp_path):
    app, client = application(tmp_path, debug=False)
    response = client.get("/")
    assert response.status_code == 200, response.text
    assert "flaxon-debug" not in response.text
    assert client.post("/__debug__/teloce/errors", json_data={}).status_code == 404
    assert client.get("/_flaxon/flaxon-debug.js").status_code == 404
    assert client.get("/__debug__").status_code == 404


def test_ssr_fallback_is_explicit(tmp_path):
    app, client = application(tmp_path, source="<template><p>{{ missing }}</p></template>")
    assert client.get("/").status_code == 500
    assert any(error["type"] == "Teloce ssr" for error in app.error_store.get_recent())
    app.teloce.options["ssr_fallback"] = "client"
    response = client.get("/")
    assert response.status_code == 200 and "data-teloce-ssr" not in response.text


def test_diagnostic_cannot_read_unregistered_source(tmp_path):
    app, client = application(tmp_path)
    client.get("/")
    (tmp_path / "secret.txt").write_text("SECRET")
    error = app.teloce.debugger.record(
        {"component": "../secret.txt", "message": "Bad", "line": 1}, client_reported=True
    )
    assert "source_excerpt" not in error


@pytest.mark.parametrize("origin", ["http://[bad", "null", "https://testserver"])
def test_malformed_origins_fail_closed(tmp_path, origin):
    app, client = application(tmp_path)
    client.get("/")
    headers = {"origin": origin, "x-flaxon-debug-token": app.teloce.debugger.token}
    assert client.post("/__debug__/teloce/errors", json_data={}, headers=headers).status_code == 403


def test_report_rate_and_invalid_locations(tmp_path):
    app, client = application(tmp_path)
    client.get("/")
    headers = {"origin": "http://testserver", "x-flaxon-debug-token": app.teloce.debugger.token}
    payload = {"filename": "http://[invalid", "path": "http://[bad", "line": "invalid"}
    assert client.post("/__debug__/teloce/errors", json_data=payload, headers=headers).status_code == 200
    app.teloce.debugger._reports = 120
    assert client.post("/__debug__/teloce/errors", json_data={}, headers=headers).status_code == 429


def test_source_map_positions_and_invalid_segments():
    from flaxon.debugging.source_maps import source_position

    mapping = {"sources": ["ui/app.html"], "mappings": "AAAA;AACA,KAAC"}
    assert source_position(mapping, 1, 1) == ("ui/app.html", 1, 1)
    assert source_position(mapping, 2, 6) == ("ui/app.html", 2, 2)
    assert source_position(mapping, 100, 1) is None
    with pytest.raises(ValueError):
        source_position({"sources": [], "mappings": "?"}, 1, 1)


def test_compile_error_keeps_debug_dashboard_available(tmp_path):
    app, client = application(tmp_path, source="<template><p>{{ run() }}</p></template>")
    assert client.get("/").status_code == 500
    errors = app.error_store.get_recent()
    assert any(item["type"] == "Teloce compile" and "SSR calls" in item["message"] for item in errors)
    assert client.get("/__debug__").status_code == 200
