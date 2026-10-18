"""Source mapping of browser diagnostics: percent-encoded paths and `location`.

Browsers percent-encode the path of a compiled component, so a dynamic page
travels as ``%5Bid%5D.js`` while the build knows it as ``[id].js``. The mapping
must decode the path first, and it must never accept a path outside the build.
"""

import pytest

from flaxon import Flaxon
from flaxon.testing import TestClient

PAGE = """<template><h1>{title}</h1></template>
<script lang="ts">
const title = signal<string>('Project');
</script>
"""

OUTPUT = "ui/pages/ProjectDetails/[id].js"


def build_app(tmp_path, page_source=PAGE):
    """Build a real project whose output includes a dynamic page."""
    ui = tmp_path / "ui"
    (ui / "pages" / "ProjectDetails").mkdir(parents=True)
    (ui / "app.html").write_text("<template><h1>Home</h1></template>", encoding="utf-8")
    (ui / "pages" / "ProjectDetails" / "[id].html").write_text(page_source, encoding="utf-8")
    app = Flaxon("mapping", debug=True)
    app.use_teloce(project_root=tmp_path, ui_dir="ui")
    app.teloce.build()
    return app


def encoded_url(app, output=OUTPUT):
    return f"{app.teloce.static_url}/{output.replace('[', '%5B').replace(']', '%5D')}"


def test_percent_encoded_dynamic_page_is_mapped(tmp_path):
    app = build_app(tmp_path)
    debugger = app.teloce.debugger
    location = debugger._map_browser_location({"filename": encoded_url(app), "line": 3, "column": 7})
    assert location is not None, "an encoded [id].js URL must map like [id].js"
    assert location["component"] == "ui/pages/ProjectDetails/[id].html"


def test_plain_dynamic_page_url_still_maps(tmp_path):
    app = build_app(tmp_path)
    debugger = app.teloce.debugger
    url = f"{app.teloce.static_url}/{OUTPUT}"
    assert debugger._map_browser_location({"filename": url, "line": 3, "column": 7}) is not None


@pytest.mark.parametrize(
    "path",
    [
        "/_flaxon/..%2f..%2fetc%2fpasswd",
        "/_flaxon/ui/..%2f..%2f..%2fetc%2fpasswd",
        "/_flaxon/%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ],
)
def test_decoded_paths_must_match_a_known_output(tmp_path, path):
    """Decoding may introduce `..`; the result must still be a build output."""
    app = build_app(tmp_path)
    debugger = app.teloce.debugger
    assert debugger._map_browser_location({"filename": path, "line": 1, "column": 1}) is None


def test_stack_position_decodes_the_url(tmp_path):
    """A stack frame only names a known output once its path is decoded."""
    app = build_app(tmp_path)
    debugger = app.teloce.debugger
    url = f"http://testserver{encoded_url(app)}"
    report = debugger._stack_position(
        {"stack": f"    at setup ({url}:3:7)\n    at mount ({url}:9:1)"}
    )
    assert report.get("filename") == url
    assert report.get("line") == "3"


def test_stack_position_ignores_an_unknown_encoded_path(tmp_path):
    app = build_app(tmp_path)
    debugger = app.teloce.debugger
    url = "http://testserver/_flaxon/ui/pages/ProjectDetails/%5Bnope%5D.js"
    assert debugger._stack_position({"stack": f"    at setup ({url}:3:7)"}) == {
        "stack": f"    at setup ({url}:3:7)"
    }


def test_location_is_returned_when_the_excerpt_cannot_be_read(tmp_path):
    """A successful mapping must not be dropped because the excerpt is missing.

    `_source_excerpt` refuses files over 200 KB, which used to throw away the
    mapped `component:line:column` as well.
    """
    padding = "x" * 210_000
    source = f"<template><h1>{{title}}</h1><!--{padding}--></template>\n" + (
        "<script lang=\"ts\">\nconst title = signal<string>('Project');\n</script>\n"
    )
    app = build_app(tmp_path, source)
    client = TestClient(app)
    client.get("/")
    response = client.post(
        "/__debug__/teloce/errors",
        json_data={
            "category": "runtime",
            "message": "signal is not defined",
            "filename": encoded_url(app),
            "line": 3,
            "column": 7,
        },
        headers={"origin": "http://testserver", "x-flaxon-debug-token": app.teloce.debugger.token},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert str(body.get("location", "")).startswith("ui/pages/ProjectDetails/[id].html:")
    assert body.get("source_excerpt") is None
