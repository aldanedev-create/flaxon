"""Teloce SPA: the browser front-end that the JSON API backs.

Covers the two things that matter for the build pipeline: the dev/prod SPA shell
is served from the root route, and the compiled production assets exist.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_spa_root_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in (r.headers.get("content-type") or "")
    body = r.content.decode("utf-8", "replace")
    # The shell mounts the Teloce app and carries the project title.
    assert ("<div id=\"app\"" in body) or ("Discord" in body)


def test_spa_does_not_mask_missing_api_routes(client):
    # A non-existent API path must fail cleanly, not silently return the SPA HTML.
    r = client.get("/api/this-route-does-not-exist")
    assert r.status_code in (401, 403, 404)
    assert "text/html" not in (r.headers.get("content-type") or "")


def test_teloce_build_artifacts_exist():
    # `python management.py build` compiles the UI into .flaxon/build. The build
    # is gitignored, so skip (rather than fail) in a clean checkout where it has
    # not been produced yet — running the build makes this test assert structure.
    manifest = ROOT / ".flaxon" / "build" / "manifest.json"
    static = ROOT / ".flaxon" / "build" / "static"
    if not manifest.exists():
        import pytest

        pytest.skip("run `python management.py build` to compile the SPA")
    assert static.exists()
