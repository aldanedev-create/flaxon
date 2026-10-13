"""Development checking follows application lifespan and saved project inputs."""

import asyncio
import threading
from types import SimpleNamespace

from flaxon import Flaxon, management


def integration(tmp_path, *, debug=True, enabled=True):
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui/app.html").write_text(
        '<script lang="ts">export default { data() { return { title: "Hi" }; } };</script>'
        "<template>{{ title }}</template>"
    )
    return Flaxon("checking", debug=debug).use_teloce(project_root=tmp_path, typecheck=enabled)


def test_startup_edit_failure_recovery_and_shutdown(tmp_path, monkeypatch):
    ui = integration(tmp_path)
    checker = ui.development_typecheck
    calls = []
    reports = []
    ui.debugger.record = reports.append

    def check(roots, *, project_root):
        calls.append((roots, project_root))
        if len(calls) == 2:
            raise RuntimeError("compiler unavailable")
        return SimpleNamespace(ok=True, findings=[])

    monkeypatch.setattr("flaxon.development_typecheck.import_attribute", lambda *_: check)

    async def scenario():
        await checker.start()
        for _ in range(100):
            if calls:
                break
            await asyncio.sleep(0.01)
        assert len(calls) == 1
        await checker.start()
        await checker.poll()
        assert len(calls) == 1
        (tmp_path / "ui/app.html").write_text("changed")
        await checker.poll()
        assert checker.error == "compiler unavailable"
        await checker.poll()
        assert len(calls) == 2
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{"strict":false}}')
        await checker.poll()
        assert len(calls) == 3 and checker.error is None
        await checker.stop()
        assert checker.task is None

    asyncio.run(scenario())
    assert calls[0][1] == tmp_path
    assert reports and reports[0]["category"] == "typecheck"


def test_production_and_opt_out_never_start_checker(tmp_path):
    for index, (debug, enabled) in enumerate(((False, True), (True, False))):
        root = tmp_path / str(index)
        root.mkdir()
        checker = integration(root, debug=debug, enabled=enabled).development_typecheck
        asyncio.run(checker.start())
        assert checker.task is None


def test_real_checker_reports_original_location_without_failing_server(tmp_path):
    ui = integration(tmp_path)
    checker = ui.development_typecheck
    checker.check()
    assert checker.result.ok and checker.error is None
    page = tmp_path / "ui/app.html"
    page.write_text(page.read_text().replace("{{ title }}", "{{ titel }}"))
    checker.check()
    assert not checker.result.ok and checker.error is None
    errors = ui.app.error_store.get_recent(10)
    assert any(error["type"] == "Teloce typecheck" and "titel" in error["message"] for error in errors)


def test_revision_includes_real_files_but_excludes_generated_and_dependencies(tmp_path):
    ui = integration(tmp_path)
    checker = ui.development_typecheck
    before = checker.fingerprint()
    for folder in ("node_modules", ".flaxon", "dist"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "ignore.ts").write_text("ignored")
    assert checker.fingerprint() == before
    (tmp_path / "utils.ts").write_text("export const value = 1;")
    assert checker.fingerprint() != before


def test_shutdown_drains_active_check_and_does_not_overlap(tmp_path, monkeypatch):
    ui = integration(tmp_path)
    checker = ui.development_typecheck
    entered, release = threading.Event(), threading.Event()
    calls = []

    def check():
        calls.append(1)
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(checker, "check", check)

    async def scenario():
        await checker.start()
        assert await asyncio.to_thread(entered.wait, 5)
        stop = asyncio.create_task(checker.stop())
        await asyncio.sleep(0.02)
        assert not stop.done()
        release.set()
        await stop
        assert checker.task is None
        assert calls == [1]

    asyncio.run(scenario())


def test_parent_child_prop_errors_reach_development_checker_and_management(tmp_path):
    ui = integration(tmp_path)
    parent = tmp_path / "ui/app.html"
    child = tmp_path / "ui/Counter.html"
    child.write_text(
        '<script lang="ts">export default { props: { count: { type: Number, required: true } } };</script>'
        "<template>{{ count }}</template>"
    )
    parent.write_text(
        '<script lang="ts">import Counter from "./Counter.html";'
        'export default { components: { Counter }, data() { return { count: "wrong" }; } };</script>'
        '<template><Counter :count="count" /></template>'
    )
    checker = ui.development_typecheck
    checker.check()
    assert not checker.result.ok
    assert any(f.file == "ui/app.html" and "number" in f.message for f in checker.result.findings)
    assert management._typecheck(ui.app, SimpleNamespace(no_templates=False, json=False)) == 1
    parent.write_text(parent.read_text().replace('count: "wrong"', "count: 3"))
    checker.check()
    assert checker.result.ok
    assert management._typecheck(ui.app, SimpleNamespace(no_templates=False, json=False)) == 0


def test_default_integration_does_not_start_checker_but_manual_command_works(tmp_path, monkeypatch):
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui/app.html").write_text(
        '<script lang="ts">const count: number = "wrong"; export default {};</script>'
        '<template><p>Hello</p></template>'
    )
    ui = Flaxon("manual-checking", debug=True).use_teloce(project_root=tmp_path)
    checker = ui.development_typecheck
    assert ui.typecheck is False

    def unexpected_check():
        raise AssertionError("Default server must not invoke type checking")

    monkeypatch.setattr(checker, "check", unexpected_check)
    asyncio.run(checker.start())
    assert checker.task is None
    assert checker.result is None
    # Compilation still succeeds; the separate checker reports the type error.
    assert ui.build()["compiled"] >= 1
    assert management._typecheck(ui.app, SimpleNamespace(no_templates=False, json=False)) == 1
