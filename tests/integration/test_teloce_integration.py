from pathlib import Path

import pytest

from flaxon import Flaxon, Request
from flaxon.modules import FlaxonModule
from flaxon.testing import TestClient


def _component(path: Path, template: str, script: str = "export default {};") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"<template>{template}</template><script>{script}</script>",
        encoding="utf-8",
    )


def test_teloce_html_shell_combines_app_and_module_pages(tmp_path: Path) -> None:
    _component(
        tmp_path / "ui" / "app.html",
        '<nav>Petal &amp; Stem</nav><main id="router-view"></main>',
    )
    module_ui = tmp_path / "modules" / "catalog" / "ui"
    _component(module_ui / "pages" / "Products.html", "<h1>Products</h1>")
    _component(module_ui / "components" / "ProductCard.html", "<article>Rose</article>")

    catalog = FlaxonModule("catalog", ui_dir=module_ui)
    app = Flaxon("Petal & Stem", debug=True)
    app.mount_module(catalog)
    app.use_teloce(project_root=tmp_path, static_url="/_ui")

    @app.get("/")
    async def home(request: Request):
        return await request.compile(
            "app.html",
            {"business": "Petal & Stem", "unsafe": "</script><script>bad()</script>"},
        )

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert 'import { mount } from "/_ui/ui/app.js"' in response.text
    assert 'import router from "/_ui/router.js"' in response.text
    assert "</script><script>bad()" not in response.text
    assert "\\u003c/script\\u003e" in response.text
    assert client.get("/_ui/ui/app.js").status_code == 200
    router = client.get("/_ui/router.js")
    assert router.status_code == 200
    assert 'path: "/products"' in router.text


def test_module_ui_can_be_registered_after_teloce(tmp_path: Path) -> None:
    _component(tmp_path / "ui" / "app.html", '<main id="router-view"></main>')
    reports_ui = tmp_path / "modules" / "reports" / "ui"
    _component(reports_ui / "pages" / "Reports.html", "<h1>Reports</h1>")

    app = Flaxon("reports", debug=True)
    integration = app.use_teloce(project_root=tmp_path)
    app.mount_module(FlaxonModule("reports", ui_dir=reports_ui))

    result = integration.build()

    assert result["failed"] == 0
    assert (tmp_path / ".flaxon" / "build" / "modules" / "reports" / "ui" / "pages" / "Reports.js").is_file()
    assert 'path: "/reports"' in (tmp_path / ".flaxon" / "build" / "router.js").read_text(encoding="utf-8")


def test_request_compile_requires_teloce() -> None:
    app = Flaxon("missing", debug=True)

    @app.get("/")
    async def home(request: Request):
        return await request.compile("app.html")

    response = TestClient(app).get("/")

    assert response.status_code == 500
    assert "Teloce is not configured" in response.text


def test_duplicate_module_page_routes_fail_at_build(tmp_path: Path) -> None:
    _component(tmp_path / "ui" / "app.html", '<main id="router-view"></main>')
    first = tmp_path / "modules" / "first" / "ui"
    second = tmp_path / "modules" / "second" / "ui"
    _component(first / "pages" / "Settings.html", "<h1>First</h1>")
    _component(second / "pages" / "Settings.html", "<h1>Second</h1>")

    app = Flaxon("collision", debug=True)
    app.mount_module(FlaxonModule("first", ui_dir=first))
    app.mount_module(FlaxonModule("second", ui_dir=second))
    integration = app.use_teloce(project_root=tmp_path)

    with pytest.raises(ValueError, match="Duplicate SPA route"):
        integration.build()


def test_production_html_entry_uses_stable_hashed_alias_and_css(tmp_path: Path) -> None:
    _component(
        tmp_path / "ui" / "app.html",
        "<main>Production</main>",
        "export default {};",
    )
    source = tmp_path / "ui" / "app.html"
    source.write_text(
        source.read_text(encoding="utf-8") + "<style>main { color: #123456; }</style>",
        encoding="utf-8",
    )
    app = Flaxon("production", debug=False)
    integration = app.use_teloce(project_root=tmp_path)

    integration.build()
    response = integration.render()

    assert (tmp_path / ".flaxon" / "build" / "ui" / "app.js").is_file()
    assert b'/_flaxon/ui/app.js' in response.body
    assert b'<link rel="stylesheet" href="/_flaxon/' in response.body
    assert b'.css">' in response.body
