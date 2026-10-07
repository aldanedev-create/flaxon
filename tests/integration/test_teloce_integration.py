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


def test_production_static_aliases_revalidate_and_router_uses_minifyjs(tmp_path, monkeypatch):
    import minifyjs
    calls=[]
    original=minifyjs.minify
    def tracked(source, **options):
        calls.append(options)
        return original(source, **options)
    monkeypatch.setattr(minifyjs,'minify',tracked)
    _component(tmp_path/'ui/app.html','<main id="router-view"></main>')
    _component(tmp_path/'ui/pages/Jobs.html','<h1>Jobs</h1>')
    app=Flaxon('cache',debug=False)
    integration=app.use_teloce(project_root=tmp_path)
    integration.build()
    client=TestClient(app)
    for path in ('/_flaxon/router.js','/_flaxon/ui/app.js'):
        assert client.get(path).headers['cache-control']=='no-cache'
    assert any(call.get('source_name')=='router.js' for call in calls)


def test_link_handler_preserves_browser_navigation(tmp_path):
    _component(tmp_path/'ui/app.html','<main id="router-view"></main>')
    _component(tmp_path/'ui/pages/Jobs.html','<h1>Jobs</h1>')
    app=Flaxon('links',debug=True)
    integration=app.use_teloce(project_root=tmp_path)
    document=integration.render().body.decode()
    assert "link.hasAttribute('download')" in document
    assert "link.target.toLowerCase() !== '_self'" in document
    assert 'router.resolve(url.pathname + url.search)' in document
    assert 'url.hash) return' in document


def test_reloader_watches_vel_but_ignores_generated_build(tmp_path):
    from flaxon.server.reload import Reloader
    watcher=Reloader()
    assert watcher._should_watch(tmp_path/'ui/App.vel')
    assert watcher._should_watch(tmp_path/'ui/app.html')
    assert not watcher._should_watch(tmp_path/'.flaxon/build/ui/app.js')


def test_navigation_listener_behavior_in_javascript(tmp_path):
    import shutil, subprocess, json
    node=shutil.which('node')
    if not node:
        pytest.skip('Node required for generated listener regression test')
    _component(tmp_path/'ui/app.html','<main id="router-view"></main>')
    _component(tmp_path/'ui/pages/Jobs.html','<h1>Jobs</h1>')
    app=Flaxon('links',debug=True)
    document=app.use_teloce(project_root=tmp_path).render().body.decode()
    start=document.index("document.addEventListener('click'")
    listener=document[start:document.index('</script>',start)].strip()
    # Execute the exact generated listener with browser-like objects.
    script='''let handler;
const document={addEventListener:(name,fn)=>handler=fn};
const location={origin:'http://localhost',pathname:'/',search:''};
let pushed=[];
const router={resolve:path=>path.startsWith('/jobs')?{}:null,push:path=>pushed.push(path)};
''' + listener + '''
function click(href,extra={}) {
 let prevented=false;
 const link={href,target:'',hasAttribute:()=>false,...extra};
 handler({target:{closest:()=>link},button:0,preventDefault:()=>prevented=true});
 return prevented;
}
if(!click('http://localhost/jobs') || pushed[0]!=='/jobs') throw Error('client route');
for(const [url,props] of [
 ['http://localhost/jobs',{target:'_blank'}],
 ['http://localhost/jobs',{hasAttribute:()=>true}],
 ['http://localhost/backend',{}],
 ['http://other/jobs',{}],
 ['http://localhost/#section',{}],
 ['mailto:someone@example.com',{}]]) {
 if(click(url,props)) throw Error('intercepted normal link '+url);
}
if(pushed.length!==1) throw Error('unexpected router calls');
'''
    subprocess.run([node,'-e',script],check=True,capture_output=True,text=True)


def test_optional_head_resources_escape_and_preserve_defaults(tmp_path):
    _component(tmp_path / "ui" / "app.html", "<h1>Hello</h1>")
    app = Flaxon("Default title", debug=True)
    integration = app.use_teloce(
        project_root=tmp_path, favicon='/static/icon.svg?a=1&b=2',
        description='A "quoted" <description>', lang='fr', theme_color='#101827',
        stylesheets=[{"href": "https://cdn.example.com/theme.css", "media": "screen"}],
        scripts=[{"src": "https://cdn.example.com/app.js", "defer": True, "async": False}],
    )
    document = integration.render(title="Page & title").body.decode()
    assert '<html lang="fr">' in document
    assert '<title>Page &amp; title</title>' in document
    assert 'A &quot;quoted&quot; &lt;description&gt;' in document
    assert 'icon.svg?a=1&amp;b=2' in document
    assert 'defer></script>' in document
    assert ' async' not in document
    assert 'name="theme-color"' in document
    plain = Flaxon("Plain", debug=True).use_teloce(project_root=tmp_path)
    document = plain.render().body.decode()
    assert '<title>Plain</title>' in document
    assert 'rel="icon"' not in document


@pytest.mark.parametrize("resource", [
    {"src": "javascript:alert(1)"}, {"src": "data:text/javascript,x"},
    {"src": "/script.js", "onload": "alert(1)"},
    {"src": "/script.js", "defer": "false"},
])
def test_head_rejects_unsafe_or_invalid_script_attributes(tmp_path, resource):
    with pytest.raises((ValueError, TypeError)):
        Flaxon("test").use_teloce(project_root=tmp_path, scripts=[resource])


def test_typescript_cdn_example_builds_and_serves(tmp_path):
    import shutil
    import importlib.util
    source = Path(__file__).resolve().parents[2] / "examples" / "teloce_head_ts"
    shutil.copytree(source, tmp_path / "example")
    spec = importlib.util.spec_from_file_location("head_example", tmp_path / "example" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = TestClient(module.app)
    response = client.get("/")
    assert response.status_code == 200
    assert 'bootstrap@5.3.3' in response.text
    assert client.get('/static/favicon.svg').status_code == 200
    assert client.get('/api/about').json()['message'].startswith('Python')
    compiled = client.get('/_flaxon/ui/units.js')
    assert compiled.status_code == 200
    assert ': number' not in compiled.text
    component = client.get('/_flaxon/ui/app.js')
    assert component.status_code == 200
    assert './units.ts' not in component.text


def test_taskboard_course_example_compiles_typed_html_and_api(tmp_path):
    import shutil
    import importlib.util
    source = Path(__file__).resolve().parents[2] / "examples/teloce_taskboard"
    shutil.copytree(source, tmp_path / "taskboard")
    spec = importlib.util.spec_from_file_location("taskboard_course", tmp_path / "taskboard/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = TestClient(module.app)
    assert client.get("/").status_code == 200
    assert client.post("/api/tasks", json_data={"title": "Ship docs"}).status_code == 201
    assert client.post("/api/tasks", json_data={"title": ""}).status_code == 422
    assert len(client.get("/api/tasks").json()["items"]) == 2
    for output in ["app.js", "api.js", "types.js", "format.js", "components/TaskRow.js"]:
        response = client.get("/_flaxon/ui/" + output)
        assert response.status_code == 200
        assert 'from "./types.ts"' not in response.text
