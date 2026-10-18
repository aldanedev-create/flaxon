"""Editor links offered by the development diagnostics endpoint.

The link is a development convenience: it is built from a validated template, only
for files inside a registered Teloce source directory, and only in debug responses.
"""

import json

import pytest

from flaxon import Flaxon
from flaxon.debugging.editor import EDITOR_PRESETS, EditorLink, resolve_editor
from flaxon.testing import TestClient

PAGE = """<template><h1>{title}</h1></template>
<script lang="ts">
const title = signal<string>('Project');
</script>
"""

OUTPUT = "ui/pages/ProjectDetails/[id].html"


def write_ui(tmp_path):
    """Create one registered UI source with a home page and a dynamic page."""
    ui = tmp_path / "ui"
    (ui / "pages" / "ProjectDetails").mkdir(parents=True)
    (ui / "app.html").write_text("<template><h1>Home</h1></template>", encoding="utf-8")
    (ui / "pages" / "ProjectDetails" / "[id].html").write_text(PAGE, encoding="utf-8")


def build_app(tmp_path, **options):
    """Build a real project with one dynamic page, then return the app."""
    write_ui(tmp_path)
    app = Flaxon("editor", debug=True)
    app.use_teloce(project_root=tmp_path, ui_dir="ui", **options)
    app.teloce.build()
    return app


def post(app):
    """Report one runtime error and return the parsed debug response."""
    client = TestClient(app)
    client.get("/")
    url = f"{app.teloce.static_url}/ui/pages/ProjectDetails/%5Bid%5D.js"
    response = client.post(
        "/__debug__/teloce/errors",
        json_data={"category": "runtime", "message": "boom", "filename": url, "line": 3, "column": 7},
        headers={"origin": "http://testserver", "x-flaxon-debug-token": app.teloce.debugger.token},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_default_preset_is_vscode():
    assert resolve_editor().template == EDITOR_PRESETS["vscode"]


@pytest.mark.parametrize("name", ["vscode", "vscode-insiders"])
def test_preset_names_are_accepted(name):
    assert resolve_editor(name).template == EDITOR_PRESETS[name]


def test_vscode_remote_preset_needs_editor_remote():
    with pytest.raises(ValueError, match="editor_remote"):
        resolve_editor("vscode-remote")
    link = resolve_editor("vscode-remote", editor_remote="ssh-remote+box")
    assert link.url_for("/work/ui/app.html", relpath="ui/app.html", line=2, column=3) == (
        "vscode://vscode-remote/ssh-remote+box/work/ui/app.html:2:3"
    )


def test_editor_none_switches_the_link_off():
    assert resolve_editor(None).template is None
    assert resolve_editor(None).url_for("/work/ui/app.html", relpath="ui/app.html", line=1, column=1) is None


@pytest.mark.parametrize(
    "template",
    [
        "no-placeholder-here",
        "http://127.0.0.1:9411/open?file={relpath}",
        "javascript:alert({path})",
        "data:text/html,{path}",
        "vbscript:open({path})",
        "file:///{path}",
        "http://127.0.0.1:9411/open?file={oops}",
    ],
)
def test_unusable_templates_are_rejected(template):
    """A template must carry {path}, known placeholders and a scheme a browser may follow."""
    with pytest.raises(ValueError):
        resolve_editor(template)


def test_custom_template_uses_the_documented_placeholders():
    template = "http://127.0.0.1:9411/open?file={path}&rel={relpath}&line={line}&column={column}"
    link = resolve_editor(template)
    assert link.url_for("/work/ui/app.html", relpath="ui/app.html", line=4, column=17) == (
        "http://127.0.0.1:9411/open?file=/work/ui/app.html&rel=ui/app.html&line=4&column=17"
    )


def test_path_map_rewrites_a_container_path():
    link = resolve_editor(editor_path_map={"/work/app": "/Users/me/app"})
    built = link.url_for("/work/app/ui/app.html", relpath="ui/app.html", line=1, column=1)
    assert built == "vscode://file//Users/me/app/ui/app.html:1:1"


def test_a_mapped_path_cannot_smuggle_a_forbidden_scheme():
    link = EditorLink(template="{path}", path_map={"/work": "file:///etc"})
    assert link.url_for("/work/ui/app.html", relpath="ui/app.html", line=1, column=1) is None


def test_debug_response_offers_a_vscode_link(tmp_path):
    app = build_app(tmp_path)
    body = post(app)
    assert body["location"].startswith(OUTPUT + ":")
    editor = body["editor_url"]
    assert editor.startswith("vscode://file/")
    assert editor.endswith(f":{body['location'].split(':')[1]}:{body['location'].split(':')[2]}")
    assert OUTPUT in editor


def test_editor_none_means_no_link(tmp_path):
    assert "editor_url" not in post(build_app(tmp_path, editor=None))


def test_a_rejected_template_fails_fast(tmp_path):
    with pytest.raises(ValueError):
        build_app(tmp_path, editor="javascript:alert({path})")


def test_codespaces_without_configuration_offers_no_link(tmp_path, monkeypatch):
    """A vscode://file link points inside the container, which the browser cannot open."""
    monkeypatch.setenv("CODESPACES", "true")
    assert "editor_url" not in post(build_app(tmp_path))


def test_codespaces_keeps_an_explicitly_configured_remote(tmp_path, monkeypatch):
    monkeypatch.setenv("CODESPACE_NAME", "box")
    app = build_app(tmp_path, editor="vscode-remote", editor_remote="ssh-remote+box")
    assert post(app)["editor_url"].startswith("vscode://vscode-remote/ssh-remote+box/")


def test_files_outside_a_registered_source_get_no_link(tmp_path):
    app = build_app(tmp_path)
    debugger = app.teloce.debugger
    assert debugger._editor_url({"location": "ui/app.html:1:2"}) is not None
    assert debugger._editor_url({"location": "../secret.html:1:2"}) is None


def test_the_stored_error_holds_no_absolute_path(tmp_path):
    app = build_app(tmp_path)
    body = post(app)
    stored = app.error_store.get(body["error_id"])
    assert str(tmp_path) not in json.dumps(stored)


def test_the_endpoint_stays_outside_debug_mode(tmp_path):
    write_ui(tmp_path)
    app = Flaxon("editor", debug=False)
    app.use_teloce(project_root=tmp_path, ui_dir="ui")
    app.teloce.build()
    client = TestClient(app)
    assert client.post("/__debug__/teloce/errors", json_data={}).status_code == 404
    assert app.teloce.debugger._editor_url({"location": "ui/app.html:1:1"}) is None
