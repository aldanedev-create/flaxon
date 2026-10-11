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
