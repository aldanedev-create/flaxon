"""``python management.py typecheck`` type-checks Teloce components and templates through pytscheck."""

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from flaxon import management
from flaxon.cli.generator import Generator


def run(root, *args):
    return subprocess.run(
        [sys.executable, str(root / "management.py"), *args],
        cwd=root.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_typecheck_passes_on_the_starter_and_catches_template_typos(tmp_path):
    pytest.importorskip("pytscheck")
    pytest.importorskip("teloce.cli.typecheck")
    root = tmp_path / "project_manager"
    Generator().generate(root)
    clean = run(root, "typecheck")
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "No type errors" in clean.stdout
    page = root / "modules/welcome/ui/Welcome.html"
    page.write_text(page.read_text().replace("{{ message }}", "{{ mesage }}"))
    broken = run(root, "typecheck")
    assert broken.returncode == 1, broken.stdout + broken.stderr
    assert "Welcome.html" in broken.stdout and "mesage" in broken.stdout
    structured = run(root, "typecheck", "--json")
    assert structured.returncode == 1, structured.stderr
    payload = json.loads(structured.stdout)
    assert not payload["ok"]
    assert any("mesage" in finding["message"] for finding in payload["findings"])
    scripts_only = run(root, "typecheck", "--no-templates")
    assert scripts_only.returncode == 0, scripts_only.stdout + scripts_only.stderr


def test_typecheck_requires_a_teloce_ui():
    with pytest.raises(ValueError, match="No Teloce UI is configured"):
        management._typecheck(SimpleNamespace(), SimpleNamespace(no_templates=False, json=False))


def test_typecheck_explains_an_outdated_teloce(monkeypatch):
    def missing(*_args, **_kwargs):
        raise ImportError("no typecheck")

    monkeypatch.setattr(management, "import_attribute", missing)
    app = SimpleNamespace(teloce=SimpleNamespace(sources=[]))
    with pytest.raises(ValueError, match=r"teloce-py\[typecheck\]"):
        management._typecheck(app, SimpleNamespace(no_templates=False, json=False))


def test_typecheck_rejects_empty_sources():
    app = SimpleNamespace(teloce=SimpleNamespace(sources=[]))
    with pytest.raises(ValueError, match="No Teloce UI source directories"):
        management._typecheck(app, SimpleNamespace(no_templates=False, json=False))


def test_typecheck_forwards_all_sources_and_operational_exit_code(monkeypatch, tmp_path):
    sources = [SimpleNamespace(directory=tmp_path / name) for name in ("app-ui", "module-ui")]
    app = SimpleNamespace(teloce=SimpleNamespace(sources=sources, project_root=tmp_path))

    def command(options):
        assert options.paths == [str(source.directory) for source in sources]
        assert options.no_templates and options.json
        assert options.no_strict is False
        return 2

    monkeypatch.setattr(management, "import_attribute", lambda *_: command)
    assert management._typecheck(app, SimpleNamespace(no_templates=True, json=True)) == 2
