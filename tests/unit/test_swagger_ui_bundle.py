"""Swagger UI ships with Flaxon, pinned and verified, so /docs works offline."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

from flaxon import Flaxon
from flaxon.openapi import SWAGGER_ASSETS, SWAGGER_UI_VERSION, SwaggerUI, swagger_asset_base
from flaxon.openapi.swagger import ASSET_DIR
from flaxon.testing import TestClient

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ASSET_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
BASE = f"/docs/assets/{SWAGGER_UI_VERSION}"


def references(html: str) -> list[str]:
    return re.findall(r'(?:src|href)="([^"]+)"', html)


# --- the vendored files are exactly what the manifest says, and pinned --------------------------


def test_every_vendored_file_matches_its_recorded_sha256():
    assert set(MANIFEST["files"]) >= {
        *SWAGGER_ASSETS,
        "LICENSE",
        "NOTICE",
        "swagger-ui-bundle.js.LICENSE.txt",
    }
    for name, expected in MANIFEST["files"].items():
        data = (ASSET_DIR / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected["sha256"], f"{name} was modified"
        assert len(data) == expected["bytes"]


def test_the_pinned_version_is_consistent_everywhere():
    assert MANIFEST["version"] == SWAGGER_UI_VERSION
    assert re.fullmatch(r"5\.\d+\.\d+", SWAGGER_UI_VERSION)
    assert MANIFEST["name"] == "swagger-ui-dist"
    assert (
        MANIFEST["source"]
        == f"https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-{SWAGGER_UI_VERSION}.tgz"
    )
    assert MANIFEST["npm_integrity"].startswith("sha512-")
    assert MANIFEST["license"] == "Apache-2.0"


def test_licenses_and_notices_travel_with_the_bundle():
    assert "Apache License" in (ASSET_DIR / "LICENSE").read_text(encoding="utf-8")
    assert "SmartBear" in (ASSET_DIR / "NOTICE").read_text(encoding="utf-8")
    assert (ASSET_DIR / "swagger-ui-bundle.js.LICENSE.txt").stat().st_size > 0
    assert b"import.meta" not in (ASSET_DIR / "swagger-ui-bundle.js").read_bytes()


def test_the_bundle_is_packaged():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "openapi/assets/swagger_ui/*" in config["tool"]["setuptools"]["package-data"]["flaxon"]


# --- the page never reaches for the internet by default ---------------------------------------


def test_default_page_loads_only_local_files_and_never_asks_a_validator():
    client = TestClient(Flaxon("docs", openapi=True))
    page = client.get("/docs")
    assert page.status_code == 200
    assert references(page.text) == [f"{BASE}/swagger-ui.css", f"{BASE}/swagger-ui-bundle.js"]
    assert "http://" not in page.text and "https://" not in page.text
    assert '"validatorUrl": null' in page.text


def test_files_are_served_with_the_right_type_long_lived_caching_and_an_etag():
    client = TestClient(Flaxon("docs", openapi=True))
    for name, media_type in SWAGGER_ASSETS.items():
        response = client.get(f"{BASE}/{name}")
        assert response.status_code == 200, name
        assert response.content == (ASSET_DIR / name).read_bytes()
        assert response.headers["content-type"] == media_type
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
        etag = response.headers["etag"]
        assert etag == f'"sha256-{MANIFEST["files"][name]["sha256"]}"'
        for header in (etag, f"W/{etag}", f'"other", {etag}', "*"):
            cached = client.get(f"{BASE}/{name}", headers={"if-none-match": header})
            assert (cached.status_code, cached.content) == (304, b""), (name, header)
        assert client.get(f"{BASE}/{name}", headers={"if-none-match": '"stale"'}).status_code == 200


def test_only_the_two_files_the_page_needs_are_served_and_only_at_the_pinned_version():
    client = TestClient(Flaxon("docs", openapi=True))
    assert client.get(f"{BASE}/swagger-ui.js").status_code == 404
    assert client.get(f"{BASE}/LICENSE").status_code == 404
    assert client.get(f"{BASE}/../swagger-ui.css").status_code in {400, 404}
    assert client.get("/docs/assets/4.0.0/swagger-ui.css").status_code == 404


def test_asset_routes_are_internal_and_stay_out_of_the_openapi_document():
    client = TestClient(Flaxon("docs", openapi=True))
    assert not [path for path in client.get("/openapi.json").json()["paths"] if "assets" in path]


def test_assets_follow_a_custom_docs_url():
    app = Flaxon("docs")
    app.enable_openapi(docs_url="/api/explorer")
    client = TestClient(app)
    base = swagger_asset_base("/api/explorer")
    assert references(client.get("/api/explorer").text) == [
        f"{base}/swagger-ui.css",
        f"{base}/swagger-ui-bundle.js",
    ]
    assert client.get(f"{base}/swagger-ui-bundle.js").status_code == 200
    assert client.get(f"{BASE}/swagger-ui-bundle.js").status_code == 404


def test_the_assets_are_public_even_when_the_docs_are_guarded():
    app = Flaxon("protected")
    app.enable_openapi(docs_guard=lambda request: request.headers.get("x-docs-key") == "letmein")
    client = TestClient(app)
    assert client.get("/docs").status_code == 403
    assert client.get(f"{BASE}/swagger-ui-bundle.js").status_code == 200


def test_no_asset_routes_without_a_swagger_page():
    app = Flaxon("docs")
    app.enable_openapi(docs_url=None)
    client = TestClient(app)
    assert client.get("/redoc").status_code == 200
    assert client.get("/docs").status_code == 404
    assert client.get(f"{BASE}/swagger-ui-bundle.js").status_code == 404


def test_an_explicit_asset_url_still_wins_and_serves_nothing_locally():
    app = Flaxon("docs")
    app.enable_openapi(swagger_asset_url="https://assets.example.test/swagger/")
    client = TestClient(app)
    assert references(client.get("/docs").text) == [
        "https://assets.example.test/swagger/swagger-ui.css",
        "https://assets.example.test/swagger/swagger-ui-bundle.js",
    ]
    assert client.get(f"{BASE}/swagger-ui-bundle.js").status_code == 404


def test_the_standalone_renderer_uses_the_bundled_files_by_default():
    assert SwaggerUI().asset_url == swagger_asset_base()
    assert SwaggerUI(asset_url="/mine/").asset_url == "/mine"


def test_redoc_and_swagger_assets_coexist():
    client = TestClient(Flaxon("docs", openapi=True))
    assert client.get("/redoc/redoc.standalone.js").status_code == 200
    assert client.get(f"{BASE}/swagger-ui.css").status_code == 200
