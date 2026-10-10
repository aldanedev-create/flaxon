"""Exercise the generated full-stack application, not just template strings."""

from __future__ import annotations

import asyncio
import secrets
import importlib
import os
import sqlite3
import sys
import tomllib
from pathlib import Path
from urllib.parse import quote, unquote
import re

import pytest

from flaxon.admin.services import AdminStore
from flaxon.cli.generator import Generator
from flaxon.cli.main import create_parser, main
from flaxon.testing import TestClient


@pytest.fixture
def starter(tmp_path, monkeypatch):
    project = tmp_path / "my-project"
    Generator().generate(project)
    monkeypatch.syspath_prepend(str(project))
    names = [
        "app",
        "settings",
        "management",
        "flaxon_cli",
        "models",
        "admin",
        "migrations",
        "modules",
        "modules.welcome",
        "modules.welcome.module",
    ]
    previous = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    try:
        yield project
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(previous)


def test_new_defaults_to_fullstack_and_keeps_basic():
    parser = create_parser()
    assert parser.parse_args(["new", "my-project"]).template == "fullstack"
    assert parser.parse_args(["new", "my-project", "--template", "basic"]).template == "basic"


def test_starter_metadata_and_literal_teloce_bindings(starter):
    metadata = tomllib.loads((starter / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "my-project"
    assert "flaxon[standard,admin]>=0.2.7" in metadata["project"]["dependencies"]
    assert "{{ projectName }}" in (starter / "modules/welcome/ui/Welcome.html").read_text()
    assert "data/" in (starter / ".gitignore").read_text()


@pytest.mark.parametrize("debug", ["1", "0"])
def test_generated_app_serves_module_ui_assets_and_protected_admin(starter, monkeypatch, debug):
    monkeypatch.setenv("FLAXON_DEBUG", debug)
    monkeypatch.setenv("FLAXON_SECRET_KEY", secrets.token_urlsafe(48))
    app = importlib.import_module("app").app
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to my-project" in response.text
    assert "https://flaxon-website.vercel.app/assets/images/logo/flaxon.png" in response.text
    assert client.get("/api/welcome/status").json()["framework"] == "Flaxon"
    assert client.get("/assets/app.css").status_code == 200
    assert client.get("/_flaxon/ui/app.js").status_code == 200
    assert client.get("/_flaxon/modules/welcome/ui/Welcome.js").status_code == 200
    assert client.get("/_flaxon/modules/welcome/ui/api.js").status_code == 200
    assert client.get("/admin").status_code == 401
    assert client.get("/admin/login").status_code == 200
    assert app._flaxon_admin_store.list("users") == {}



def test_admin_setup_hashes_persists_and_authenticates(starter, monkeypatch):
    management = importlib.import_module("management")
    password = secrets.token_urlsafe(20) + "Aa1!"
    monkeypatch.setattr(__import__("flaxon.management", fromlist=["getpass"]).getpass, "getpass", lambda prompt: password)
    assert management.main(["setup-admin", "--username", "owner"]) == 0
    store = AdminStore(str(starter / "data/admin.sqlite3"))
    record = store.get("users", "owner")
    assert "password" not in record
    assert record["password_hash"] != password
    assert record["permissions"] == ["admin.superuser"]
    app = importlib.import_module("app").app
    dashboard = app._flaxon_admin_dashboard
    token = asyncio.run(dashboard.auth.login("owner", password))
    assert token
    client = TestClient(app)
    response = client.get("/admin/profile", headers={"cookie": f"session_id={token}"})
    assert response.status_code == 200
    assert "Profile" in response.text
    with pytest.raises(SystemExit) as error:
        management.main(["createsuperuser", "--username", "owner"])
    assert error.value.code == 1
    assert store.get("users", "owner") == record


@pytest.mark.parametrize("debug", ["1", "0"])
@pytest.mark.parametrize("command", ["setup-admin", "createsuperuser"])
@pytest.mark.parametrize("password", ["a", "LongUniquePassword9!"])
def test_admin_setup_accepts_chosen_password_with_production_advice(
    starter, monkeypatch, capsys, debug, command, password
):
    monkeypatch.setenv("FLAXON_DEBUG", debug)
    monkeypatch.setenv("FLAXON_SECRET_KEY", secrets.token_urlsafe(48))
    management = importlib.import_module("management")
    monkeypatch.setattr(__import__("flaxon.management", fromlist=["getpass"]).getpass, "getpass", lambda prompt: password)
    assert management.main([command, "--username", "owner"]) == 0
    app = importlib.import_module("app").app
    assert app._flaxon_admin_dashboard.auth.verify("owner", password)
    record = AdminStore(str(starter / "data/admin.sqlite3")).get("users", "owner")
    assert "password" not in record
    assert record["password_hash"] != password
    error_output = capsys.readouterr().err
    assert ("recommended strength" in error_output) == (debug == "0" and password == "a")


@pytest.mark.parametrize("passwords", [("", ""), ("x" * 129, "x" * 129), ("Welcome123!", "different")])
def test_invalid_admin_passwords_create_no_account(starter, monkeypatch, passwords):
    management = importlib.import_module("management")
    answers = iter(passwords)
    monkeypatch.setattr(__import__("flaxon.management", fromlist=["getpass"]).getpass, "getpass", lambda prompt: next(answers))
    with pytest.raises(SystemExit) as error:
        management.main(["setup-admin", "--username", "owner"])
    assert error.value.code == 1
    assert AdminStore(str(starter / "data/admin.sqlite3")).list("users") == {}


def test_generator_preserves_existing_files_and_rejects_unknown_templates(tmp_path):
    path = tmp_path / "existing"
    path.mkdir()
    (path / "app.py").write_text("keep me")
    with pytest.raises(FileExistsError):
        Generator().generate(path)
    assert (path / "app.py").read_text() == "keep me"
    with pytest.raises(ValueError):
        Generator().generate(tmp_path / "invalid", "unknown")
    assert not (tmp_path / "invalid").exists()
    basic = tmp_path / "basic"
    Generator().generate(basic, "basic")
    assert (basic / "app.py").is_file()
    assert not (basic / "management.py").exists()


def test_docs_directory_lists_every_document_and_getting_started_links_exist():
    docs = Path(__file__).resolve().parents[2] / "docs"
    index = (docs / "index.md").read_text()
    for page in docs.rglob("*.md"):
        if page != docs / "index.md":
            assert f"({quote(page.relative_to(docs).as_posix(), safe='/')})" in index
    for name in ["index.md", "getting-started.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", (docs / name).read_text()):
            if "://" not in target:
                assert (docs / unquote(target.split("#")[0])).is_file(), target


def test_new_command_generates_project_and_prints_management_steps(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["flaxon", "new", "hello-flaxon", "--no-venv"])
    assert main() == 0
    assert (tmp_path / "hello-flaxon/management.py").is_file()
    output = capsys.readouterr().out
    assert "management.py migrate" in output
    assert "management.py setup-admin" in output
    assert main() == 1


@pytest.mark.skipif(
    os.getenv("FLAXON_BROWSER_TESTS") != "1",
    reason="Set FLAXON_BROWSER_TESTS=1 and install Playwright Chromium",
)
def test_generated_welcome_browser_calls_python_and_opens_admin(starter):
    import socket
    import threading
    import time

    import uvicorn
    from playwright.sync_api import sync_playwright

    app = importlib.import_module("app").app
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Generated application did not start")
            time.sleep(0.05)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            # Keep the browser check independent of the external logo host.
            logo = Path(__file__).resolve().parents[2] / "assets/flaxon.png"
            page.route(
                "https://flaxon-website.vercel.app/assets/images/logo/flaxon.png",
                lambda route: route.fulfill(content_type="image/png", body=logo.read_bytes()),
            )
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/")
            page.get_by_role("heading", name="The installation worked successfully!").wait_for()
            page.get_by_text("Welcome to my-project.").wait_for()
            page.get_by_role("link", name="Try the Jinax example").click()
            page.get_by_role("heading", name="A complete page, rendered with Jinax.").wait_for()
            page.get_by_role("link", name="Back to the welcome page").click()
            page.get_by_role("button", name="Try your Python API").click()
            page.get_by_role("status").filter(has_text="talking to a Flaxon module").wait_for()
            page.get_by_role("link", name="Open your admin").click()
            page.locator('input[name="password"]').wait_for()
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_module_owned_custom_commands_run_via_real_cli(starter, monkeypatch, capsys):
    monkeypatch.chdir(starter)
    monkeypatch.setattr(sys, "argv", ["flaxon", "welcome"])
    assert main() == 0
    assert "Welcome to my-project." in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["flaxon", "welcome-status"])
    assert main() == 0
    assert "talking to a Flaxon module" in capsys.readouterr().out
    assert not (starter / "data").exists(), "Custom commands must not start the app or create its database"


def test_jinax_is_a_complete_server_rendered_option(starter):
    app = importlib.import_module("app").app
    response = TestClient(app).get("/server-page")
    assert response.status_code == 200
    assert "Welcome to my-project" in response.text
    assert "Teloce is optional" in response.text
    assert "<!doctype html>" in response.text
    assert "/_flaxon/" not in response.text
    assert "https://flaxon-website.vercel.app/docs.html" in response.text


def test_custom_commands_are_discovered_in_fresh_python_processes(starter):
    import subprocess

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(Path(path).resolve()) for path in sys.path if path)
    for command in ["welcome", "welcome-status"]:
        result = subprocess.run(
            [sys.executable, "-m", "flaxon.cli.main", command],
            cwd=starter,
            env=env,
            text=True,
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        expected = "Welcome to my-project" if command == "welcome" else "talking to a Flaxon module"
        assert expected in result.stdout
    assert not (starter / "data").exists()


def test_management_build_produces_production_ui_without_storage(starter, monkeypatch):
    monkeypatch.chdir(starter)
    management = importlib.import_module("management")
    assert management.main(["build"]) == 0
    app = importlib.import_module("app").app
    assert app.debug is False
    assert app.teloce.options["minifier"] == "minifyjs"
    assert app.teloce.options["production"] is True
    assert (app.teloce.build_dir / "ui/app.js").is_file()
    assert list(app.teloce.build_dir.rglob("*.css"))
    assert list(app.teloce.build_dir.rglob("*.bundle-*.js"))
    assert not (starter / "data").exists()
    assert not list(starter.rglob("*.sqlite3"))
    assert not (app.teloce.build_dir / "flaxon-debug.js").exists()


def test_management_build_failure_stops_deployment(starter, monkeypatch):
    monkeypatch.chdir(starter)
    from flaxon.teloce import Teloce

    monkeypatch.setattr(Teloce, "build", lambda self: {"failed": 1, "errors": []})
    management = importlib.import_module("management")
    with pytest.raises(SystemExit) as error:
        management.main(["build"])
    assert error.value.code == 1
    assert not (starter / "data").exists()


def test_management_build_reports_missing_ui(starter, monkeypatch):
    monkeypatch.chdir(starter)
    from flaxon import management as commands
    from types import SimpleNamespace

    monkeypatch.setattr(commands, "load_application", lambda path: SimpleNamespace())
    with pytest.raises(SystemExit) as error:
        importlib.import_module("management").main(["build"])
    assert error.value.code == 1
