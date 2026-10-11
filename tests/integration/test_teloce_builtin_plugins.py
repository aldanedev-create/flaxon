"""First-party Teloce modules are optional in Flaxon shells and SSR metadata."""

import json
from pathlib import Path

import pytest

from flaxon import Flaxon, Request
from flaxon.testing import TestClient


def project(tmp_path: Path, plugins=None):
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui/app.html").write_text(
        "<template><h1>Tasks</h1></template><script>export default {}</script>"
    )
    app = Flaxon("plugins", debug=True)
    ui = app.use_teloce(project_root=tmp_path, plugins=plugins)

    @app.get("/")
    async def home(request: Request):
        return await request.compile(meta={"title": "Page", "description": "Page description"})

    return TestClient(app), ui


def test_enabled_plugins_and_server_metadata(tmp_path):
    client, ui = project(
        tmp_path,
        {
            "forms": True,
            "head": {"title": "Default", "description": "Default text"},
            "pwa": {"name": "Tasks"},
        },
    )
    page = client.get("/")
    assert page.status_code == 200
    assert "await installPlugins(" in page.text
    assert '"title": "Page"' in page.text
    assert "<title>Page</title>" in page.text
    assert 'data-teloce-head name="description" content="Page description"' in page.text
    assert 'rel="manifest"' in page.text
    assert client.get("/_flaxon/teloce-plugins/forms.js").status_code == 200
    worker = client.get("/teloce-sw.js")
    assert worker.status_code == 200
    assert worker.headers["service-worker-allowed"] == "/"
    assert "application/javascript" in worker.headers["content-type"]
    assert "/_flaxon/ui/app.js" in worker.text
    assert "/api/" not in worker.text
    manifest = client.get("/_flaxon/teloce-plugins/manifest.webmanifest")
    assert json.loads(manifest.text)["name"] == "Tasks"
    assert ui.options["plugins"]["pwa"]["workerURL"] == "/teloce-sw.js"


def test_no_plugin_configuration_leaves_shell_unchanged(tmp_path):
    client, ui = project(tmp_path)
    assert "installPlugins" not in client.get("/").text
    assert not (ui.build_dir / "teloce-plugins").exists()
    assert client.get("/teloce-sw.js").status_code == 404


def test_reject_external_worker_and_do_not_mutate_settings(tmp_path):
    config = {"pwa": {"name": "Tasks"}}
    _, ui = project(tmp_path, config)
    assert "workerURL" not in config["pwa"]
    assert ui.options["plugins"]["pwa"]["workerURL"] == "/teloce-sw.js"
    with pytest.raises(ValueError, match="same-origin"):
        Flaxon("invalid").use_teloce(
            project_root=tmp_path, plugins={"pwa": {"workerURL": "https://other.test/sw.js"}}
        )
