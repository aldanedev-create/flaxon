"""`flaxon new --template`: every template must generate a project that actually works."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from flaxon.cli.commands.new import NewCommand
from flaxon.cli.console import Console
from flaxon.cli.generator import Generator
from flaxon.cli.main import create_parser, main
from flaxon.cli.project_templates import DEFAULT_TEMPLATE, TEMPLATES, detect_template, template_names

NEW_TEMPLATES = ["api", "api-db", "web"]
ROOT = Path(__file__).resolve().parents[2]


def run(project: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=project, capture_output=True, text=True, timeout=timeout, check=False
    )


def test_registry_is_consistent():
    assert template_names() == ["basic", "api", "api-db", "web", "fullstack"]
    assert DEFAULT_TEMPLATE == "fullstack"
    for name, template in TEMPLATES.items():
        assert template.name == name and template.summary and template.steps
        if template.source:
            directory = ROOT / "src/flaxon/cli" / template.source
            assert list(directory.rglob("*.tmpl")), f"{name} has no template files"


def test_every_starter_directory_is_packaged():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    patterns = data["tool"]["setuptools"]["package-data"]["flaxon"]
    for template in TEMPLATES.values():
        if template.source:
            assert f"cli/{template.source.split('/')[0]}/**/*.tmpl" in patterns


def test_parser_accepts_every_template_and_rejects_unknown():
    parser = create_parser()
    for name in template_names():
        assert parser.parse_args(["new", "demo", "--template", name]).template == name
    with pytest.raises(SystemExit):
        parser.parse_args(["new", "demo", "--template", "nope"])


def test_list_templates_output(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["flaxon", "new", "--list-templates"])
    assert main() == 0
    output = capsys.readouterr().out
    for name, template in TEMPLATES.items():
        assert name in output and template.summary in output


def test_new_without_directory_is_an_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["flaxon", "new"])
    assert main() == 2
    assert "Provide a project directory" in capsys.readouterr().err


@pytest.mark.parametrize("template", NEW_TEMPLATES)
def test_lean_templates_exclude_heavy_features(tmp_path, template):
    project = tmp_path / "demo"
    Generator().generate(project, template)
    names = {p.relative_to(project).as_posix() for p in project.rglob("*") if p.is_file()}
    assert {
        "app.py",
        "requirements.txt",
        "requirements-dev.txt",
        "README.md",
        ".gitignore",
        "pytest.ini",
    } <= names
    assert not {"admin.py", "flaxon_cli.py"} & names
    assert not any(n.startswith(("ui/", "modules/welcome")) for n in names)
    assert "teloce" not in (project / "requirements.txt").read_text().lower()
    assert detect_template(project) == template


def test_template_requirements(tmp_path):
    expected = {
        "api": "flaxon[standard]>=0.3.0\n",
        "web": "flaxon[standard]>=0.3.0\n",
        "api-db": "flaxon[standard,orm]>=0.3.0\n",
    }
    for template, text in expected.items():
        project = tmp_path / template
        Generator().generate(project, template)
        assert (project / "requirements.txt").read_text() == text
        assert (project / "requirements-dev.txt").read_text().startswith("-r requirements.txt\n")


@pytest.mark.parametrize("template", NEW_TEMPLATES)
def test_generated_project_passes_its_own_tests(tmp_path, template):
    project = tmp_path / f"demo-{template}"
    Generator().generate(project, template)
    result = run(project, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("template", "forbidden"),
    [
        ("api", {"teloce", "minifyjs", "pytscheck", "tortoise"}),
        ("web", {"teloce", "minifyjs", "pytscheck", "tortoise"}),
        ("api-db", {"teloce", "minifyjs", "pytscheck"}),
    ],
)
def test_lean_apps_never_import_optional_stacks(tmp_path, template, forbidden):
    """Guards the dependency diet: a lean app must not need Teloce, MinifyJS or pytscheck."""
    project = tmp_path / "lean"
    Generator().generate(project, template)
    code = (
        "import sys, app\n"
        f"leaked = sorted(n for n in {sorted(forbidden)!r} if n in sys.modules)\n"
        "print('LEAKED', leaked)\n"
        "raise SystemExit(1 if leaked else 0)\n"
    )
    result = run(project, "-c", code)
    assert result.returncode == 0, result.stdout + result.stderr


def test_api_db_management_flow_creates_and_applies_migration(tmp_path):
    project = tmp_path / "flow"
    Generator().generate(project, "api-db")
    for command in ("check", "makemigrations", "migrate"):
        result = run(project, "management.py", command)
        assert result.returncode == 0, f"{command}: {result.stdout}{result.stderr}"
    assert (project / "migrations/0001_initial.py").is_file()
    assert (project / "data/app.sqlite3").is_file()


@pytest.mark.parametrize(
    ("template", "present", "absent"),
    [
        ("api", "-m pytest", "setup-admin"),
        ("web", "-m flaxon run app:app", "management.py"),
        ("api-db", "management.py migrate", "setup-admin"),
        ("fullstack", "management.py setup-admin", "-m pytest"),
        ("basic", "-m flaxon run app:app --reload", "-m pytest"),
    ],
)
def test_next_steps_match_the_template(tmp_path, monkeypatch, capsys, template, present, absent):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["flaxon", "new", "demo", "--template", template, "--no-venv"])
    assert main() == 0
    output = capsys.readouterr().out
    assert present in output and absent not in output
    if template in NEW_TEMPLATES:
        assert "-r requirements-dev.txt" in output


def test_resume_detects_the_template(tmp_path, monkeypatch, capsys):
    project = tmp_path / "resume"
    Generator().generate(project, "api-db")
    monkeypatch.setattr(NewCommand, "_create_environment", lambda *args, **kwargs: None)
    args = create_parser(include_project=False).parse_args(["new", str(project), "--resume-venv"])
    assert NewCommand()._run(args, Console(color=False)) == 0
    output = capsys.readouterr().out
    assert "management.py migrate" in output and "setup-admin" not in output


def test_basic_starter_serves_interactive_docs_without_route_collisions(tmp_path):
    """The framework already serves /health, so the starter must not define it again."""
    project = tmp_path / "basic-app"
    Generator().generate(project, "basic")
    code = (
        "import warnings\n"
        "warnings.simplefilter('error')\n"
        "import app\n"
        "from flaxon.testing import TestClient\n"
        "client = TestClient(app.app)\n"
        "assert client.get('/docs').status_code == 200\n"
        "assert client.get('/health').status_code == 200\n"
        "assert client.get('/').json()['message'] == 'Hello from basic-app'\n"
    )
    result = run(project, "-c", code)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "collision" not in result.stderr.lower()
