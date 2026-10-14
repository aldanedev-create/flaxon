"""Development rebuilds follow saved UI inputs without overlapping builds."""

import asyncio
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from flaxon import Flaxon
from flaxon.exceptions import HTTPException


def integration(tmp_path: Path, debug: bool = True):
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui/app.html").write_text("<h1>Hello</h1>")
    return Flaxon("reload", debug=debug).use_teloce(project_root=tmp_path)


def test_revision_tracks_ui_inputs_and_excludes_outputs(tmp_path):
    ui = integration(tmp_path)
    first = ui._source_revision()
    output = tmp_path / "ui/generated"
    output.mkdir()
    ui.build_dir = output
    (output / "app.js").write_text("generated")
    assert ui._source_revision() == first
    for suffix in ("html", "ts", "js", "css"):
        path = tmp_path / f"ui/extra.{suffix}"
        path.write_text("changed")
        changed = ui._source_revision()
        assert changed != first
        path.unlink()
        assert ui._source_revision() == first
    module = tmp_path / "module-ui"
    module.mkdir()
    ui.register_source("module", module)
    (module / "Page.html").write_text("module")
    assert ui._source_revision() != first


def test_concurrent_polls_rebuild_once_and_retry_after_edit(tmp_path):
    ui = integration(tmp_path)
    ui.debugger._authorize = lambda request: None
    builds = []

    def build():
        builds.append(1)
        ui._dev_revision = ui._source_revision()
        ui.build_result = {"failed": False}

    ui.build = build

    async def scenario():
        async def poll():
            await asyncio.gather(*(ui.development_reload(SimpleNamespace()) for _ in range(4)))

        await poll()
        assert len(builds) == 1
        await poll()
        assert len(builds) == 1
        (tmp_path / "ui/app.html").write_text("<h1>Changed</h1>")
        await poll()
        assert len(builds) == 2

    asyncio.run(scenario())


def test_failed_build_does_not_repeat_until_sources_change(tmp_path):
    ui = integration(tmp_path)
    ui.debugger._authorize = lambda request: None
    ui.debugger.record = lambda report: None
    builds = []

    def build():
        builds.append(1)
        raise ValueError("bad template")

    ui.build = build

    async def poll():
        await ui.development_reload(SimpleNamespace())
        await ui.development_reload(SimpleNamespace())

    asyncio.run(poll())
    assert len(builds) == 1
    assert ui.build_result["failed"]


def test_production_rejects_reload_requests(tmp_path):
    """Production never enables the development transport."""

    ui = integration(tmp_path, debug=False)
    with pytest.raises(HTTPException) as failure:
        asyncio.run(ui.development_reload(SimpleNamespace()))
    assert failure.value.status_code == 404


def test_browser_reload_poll_and_cleanup(tmp_path):
    """The injected client reloads successful revisions and cancels polling."""

    if not shutil.which("node"):
        pytest.skip("Node required")
    client = Path(__file__).parents[2] / "src/flaxon/debugging/teloce-client.js"
    module = tmp_path / "client.mjs"
    module.write_text(client.read_text())
    script = tmp_path / "check.mjs"
    script.write_text(f"""
import assert from 'node:assert/strict';
import {{installTeloceDebugger}} from {module.as_uri()!r};
let timer, cleared=false, reloads=0;
globalThis.setTimeout=fn=>{{timer=fn;return 1}};
globalThis.clearTimeout=()=>{{cleared=true}};
globalThis.location={{reload(){{reloads++}}}};
globalThis.window={{fetch:async()=>({{ok:true,status:200,json:async()=>({{revision:'new',failed:false}})}}),addEventListener(){{}},removeEventListener(){{}}}};
const cleanup=installTeloceDebugger({{token:'token',revision:'old'}});
await timer();assert.equal(reloads,1);
cleanup();assert.equal(cleared,true);
""")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def authorize(ui, *, origin, host="127.0.0.1:8000", scheme="http", token=None):
    headers = {
        "origin": origin,
        "host": host,
        "x-flaxon-debug-token": ui.debugger.token if token is None else token,
        "content-length": "0",
    }
    ui.debugger._authorize(SimpleNamespace(scope={"scheme": scheme}, headers=headers))


def rejection(ui, **kwargs):
    with pytest.raises(HTTPException) as failure:
        authorize(ui, **kwargs)
    assert failure.value.status_code == 403
    return failure.value


def test_same_origin_with_valid_token_is_accepted(tmp_path):
    authorize(integration(tmp_path), origin="http://127.0.0.1:8000")


def test_origin_mismatch_is_reported_as_origin_not_token(tmp_path):
    """Behind a proxy the browser's https origin differs from the scheme the server sees."""

    ui = integration(tmp_path)
    failure = rejection(ui, origin="https://127.0.0.1:8000")
    assert failure.code == "FX-DEBUG-ORIGIN"
    assert "https://127.0.0.1:8000" in failure.detail
    assert "http://127.0.0.1:8000" in failure.detail
    assert "--forwarded-allow-ips" in failure.detail


def test_origin_host_and_missing_origin_are_origin_rejections(tmp_path):
    ui = integration(tmp_path)
    assert rejection(ui, origin="http://localhost:8000").code == "FX-DEBUG-ORIGIN"
    assert rejection(ui, origin="").code == "FX-DEBUG-ORIGIN"
    assert "no Origin" in rejection(ui, origin="").detail


def test_stale_token_is_reported_as_token_rejection(tmp_path):
    failure = rejection(integration(tmp_path), origin="http://127.0.0.1:8000", token="from-before-restart")
    assert failure.code == "FX-DEBUG-TOKEN"


def test_origin_is_checked_before_token(tmp_path):
    """A wrong origin must never look like a stale token, or the browser would reload forever."""

    failure = rejection(integration(tmp_path), origin="https://elsewhere.test", token="wrong")
    assert failure.code == "FX-DEBUG-ORIGIN"


def run_client_scenario(tmp_path, body):
    if not shutil.which("node"):
        pytest.skip("Node required")
    client = Path(__file__).parents[2] / "src/flaxon/debugging/teloce-client.js"
    module = tmp_path / "client.mjs"
    module.write_text(client.read_text())
    script = tmp_path / "check.mjs"
    script.write_text(
        f"""
import assert from 'node:assert/strict';
import {{installTeloceDebugger}} from {module.as_uri()!r};
const timers = []; let reloads = 0; const notices = []; const store = new Map();
globalThis.setTimeout = fn => {{ timers.push(fn); return timers.length; }};
globalThis.clearTimeout = () => {{}};
globalThis.location = {{ reload() {{ reloads++; }} }};
globalThis.sessionStorage = {{ getItem: k => store.get(k) ?? null,
  setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) }};
const element = () => ({{ style: {{}}, kids: [], setAttribute() {{}}, remove() {{}},
  append(...c) {{ this.kids.push(...c); }} }});
globalThis.document = {{ hidden: false, createElement: element,
  addEventListener() {{}}, removeEventListener() {{}},
  body: {{ append(node) {{ notices.push(node.kids[0].textContent); }} }} }};
const reply = (status, payload) => async () => (
  {{ ok: status < 300, status, json: async () => payload }});
globalThis.window = {{ fetch: reply(200, {{}}), addEventListener() {{}}, removeEventListener() {{}} }};
{body}
"""
    )
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_client_stops_without_reloading_when_origin_is_rejected(tmp_path):
    run_client_scenario(
        tmp_path,
        """
globalThis.window.fetch = reply(403, {
  error: { code: 'FX-DEBUG-ORIGIN', message: 'sent https://x, server sees http://x' } });
installTeloceDebugger({ token: 't', revision: 'r' });
await timers.shift()();
assert.equal(reloads, 0);
assert.equal(timers.length, 0);
assert.match(notices[0], /sent https:\\/\\/x, server sees http:\\/\\/x/);
""",
    )


def test_client_reloads_once_for_a_stale_token_then_stops(tmp_path):
    run_client_scenario(
        tmp_path,
        """
globalThis.window.fetch = reply(403, { error: { code: 'FX-DEBUG-TOKEN', message: 'stale' } });
installTeloceDebugger({ token: 't', revision: 'r' });
await timers.shift()();
assert.equal(reloads, 1);
installTeloceDebugger({ token: 't', revision: 'r' });
await timers.shift()();
assert.equal(reloads, 1);
assert.equal(timers.length, 0);
assert.equal(notices.length, 1);
""",
    )


def test_client_stops_reloading_when_every_poll_changes_the_revision(tmp_path):
    run_client_scenario(
        tmp_path,
        """
let n = 0;
globalThis.window.fetch = async () => ({ ok: true, status: 200,
  json: async () => ({ revision: 'r' + ++n, failed: false }) });
for (let i = 0; i < 20; i++) {
  installTeloceDebugger({ token: 't', revision: 'r0' });
  if (!timers.length) break;
  await timers.shift()();
}
assert.equal(reloads, 6);
assert.match(notices.at(-1), /reload loop/);
""",
    )