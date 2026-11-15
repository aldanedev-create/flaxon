"""ReDoc ships with Flaxon, pinned and verified, so /redoc works offline."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

from flaxon import Flaxon
from flaxon.openapi import REDOC_VERSION, ReDoc, redoc_asset_url
from flaxon.openapi.redoc import ASSET_DIR, BUNDLE_NAME
from flaxon.testing import TestClient

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ASSET_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
BUNDLE = (ASSET_DIR / BUNDLE_NAME).read_bytes()


def script_sources(html: str) -> list[str]:
    return re.findall(r'<script[^>]*\ssrc="([^"]+)"', html)


# --- the vendored files are exactly what the manifest says, and pinned --------------------------


def test_every_vendored_file_matches_its_recorded_sha256():
    assert set(MANIFEST["files"]) >= {BUNDLE_NAME, "LICENSE", f"{BUNDLE_NAME}.LICENSE.txt"}
    for name, expected in MANIFEST["files"].items():
        data = (ASSET_DIR / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected["sha256"], f"{name} was modified"
        assert len(data) == expected["bytes"]


def test_the_pinned_version_is_consistent_everywhere():
    assert MANIFEST["version"] == REDOC_VERSION
    assert re.fullmatch(r"2\.\d+\.\d+", REDOC_VERSION), "only the 2.x classic-script bundle is supported"
    assert MANIFEST["source"] == f"https://registry.npmjs.org/redoc/-/redoc-{REDOC_VERSION}.tgz"
    assert MANIFEST["npm_integrity"].startswith("sha512-")
    assert f'Version: "{REDOC_VERSION}"' in (ASSET_DIR / f"{BUNDLE_NAME}.LICENSE.txt").read_text(
        encoding="utf-8"
    )


def test_the_bundle_is_a_classic_script_and_its_licenses_travel_with_it():
    assert b"import.meta" not in BUNDLE, "ES-module bundles cannot be loaded with a plain <script> tag"
    assert b"redoc.standalone.js.LICENSE.txt" in BUNDLE[:200]
    assert "MIT License" in (ASSET_DIR / "LICENSE").read_text(encoding="utf-8")
    notices = (ASSET_DIR / f"{BUNDLE_NAME}.LICENSE.txt").read_text(encoding="utf-8")
    assert "DOMPurify" in notices and "React" in notices


def test_the_bundle_is_packaged():
    patterns = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]["package-data"][
        "flaxon"
    ]
    assert "openapi/assets/redoc/*" in patterns


# --- the page never reaches for the internet by default ---------------------------------------


def test_default_page_loads_only_the_local_bundle():
    client = TestClient(Flaxon("docs", openapi=True))
    page = client.get("/redoc")
    assert page.status_code == 200
    assert script_sources(page.text) == [f"/redoc/{BUNDLE_NAME}?v={REDOC_VERSION}"]
    assert "http://" not in page.text and "https://" not in page.text


def test_bundle_is_served_with_long_lived_caching_and_an_etag():
    client = TestClient(Flaxon("docs", openapi=True))
    response = client.get(f"/redoc/{BUNDLE_NAME}", query={"v": REDOC_VERSION})
    assert response.status_code == 200
    assert response.content == BUNDLE
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    etag = response.headers["etag"]
    assert etag == f'"sha256-{MANIFEST["files"][BUNDLE_NAME]["sha256"]}"'
    for header in (etag, f"W/{etag}", f'"other", {etag}', "*"):
        cached = client.get(f"/redoc/{BUNDLE_NAME}", headers={"if-none-match": header})
        assert cached.status_code == 304, header
        assert cached.content == b""
    assert client.get(f"/redoc/{BUNDLE_NAME}", headers={"if-none-match": '"stale"'}).status_code == 200


def test_the_asset_route_is_internal_and_stays_out_of_the_openapi_document():
    client = TestClient(Flaxon("docs", openapi=True))
    assert not [path for path in client.get("/openapi.json").json()["paths"] if "redoc" in path]


def test_asset_follows_a_custom_redoc_url():
    app = Flaxon("docs")
    app.enable_openapi(redoc_url="/api/reference")
    client = TestClient(app)
    assert script_sources(client.get("/api/reference").text) == [
        f"/api/reference/{BUNDLE_NAME}?v={REDOC_VERSION}"
    ]
    assert client.get(f"/api/reference/{BUNDLE_NAME}").content == BUNDLE
    assert client.get("/redoc").status_code == 404


def test_the_asset_is_public_even_when_the_docs_are_guarded():
    app = Flaxon("protected")
    app.enable_openapi(docs_guard=lambda request: request.headers.get("x-docs-key") == "letmein")
    client = TestClient(app)
    assert client.get("/redoc").status_code == 403
    assert client.get(f"/redoc/{BUNDLE_NAME}").status_code == 200


def test_no_asset_route_without_a_redoc_page():
    app = Flaxon("docs")
    app.enable_openapi(redoc_url=None)
    client = TestClient(app)
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 404
    assert client.get(f"/redoc/{BUNDLE_NAME}").status_code == 404


def test_an_explicit_asset_url_still_wins_and_serves_nothing_locally():
    app = Flaxon("docs")
    app.enable_openapi(redoc_asset_url="https://assets.example.test/redoc.js")
    client = TestClient(app)
    assert script_sources(client.get("/redoc").text) == ["https://assets.example.test/redoc.js"]
    assert client.get(f"/redoc/{BUNDLE_NAME}").status_code == 404


def test_the_standalone_renderer_uses_the_bundled_url_by_default():
    assert script_sources(ReDoc().render().body.decode()) == [redoc_asset_url()]
    assert script_sources(ReDoc(asset_url="/mine.js").render().body.decode()) == ["/mine.js"]
