import sys
from types import SimpleNamespace

import pytest

from flaxon.cli.commands import run as run_module
from flaxon.cli.main import create_parser, main


def test_cli_registers_builtin_commands():
    parser = create_parser()
    for command in ("run", "routes", "doctor", "docs", "inspect", "migrate", "test", "worker"):
        args = parser.parse_args([command, "app:app"] if command not in {"migrate", "test"} else [command])
        assert args.command == command


def test_cli_routes_accepts_output_options():
    args = create_parser().parse_args(["routes", "app:app", "--format", "json", "--output", "routes.json"])
    assert args.format == "json"
    assert args.output == "routes.json"


def test_cli_version(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["flaxon", "--version"])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    assert "Flaxon" in capsys.readouterr().out


def test_new_does_not_import_project_commands(tmp_path, monkeypatch):
    (tmp_path / "flaxon_cli.py").write_text("raise RuntimeError('application imported')\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["flaxon", "new", "example", "--no-venv"])
    assert main() == 0
    assert (tmp_path / "example" / "management.py").exists()


def test_commands_are_discovered_once(monkeypatch):
    from flaxon.cli.discovery import CommandDiscovery
    original = CommandDiscovery.discover
    calls = []
    def discover(self, **options):
        calls.append(options)
        return original(self, **options)
    monkeypatch.setattr(CommandDiscovery, "discover", discover)
    monkeypatch.setattr(sys, "argv", ["flaxon", "version"])
    assert main() == 0
    assert calls == [{"include_project": False}]


def test_environment_timeout_terminates_process(monkeypatch, tmp_path):
    import subprocess
    from flaxon.cli.commands.new import NewCommand
    from flaxon.cli.console import Console
    class Process:
        stopped = False
        def wait(self, timeout=None):
            if not self.stopped:
                raise subprocess.TimeoutExpired("venv", timeout)
            return 0
        def poll(self):
            return 0 if self.stopped else None
        def terminate(self):
            self.stopped = True
    process = Process()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    clock = iter([0, 0, 121])
    monkeypatch.setattr("flaxon.cli.commands.new.time.monotonic", lambda: next(clock))
    with pytest.raises(subprocess.TimeoutExpired):
        NewCommand._create_environment(tmp_path, Console(color=False))
    assert process.stopped


def _run_with_fake_uvicorn(monkeypatch, argv):
    captured = {}
    fake_uvicorn = SimpleNamespace(run=lambda *args, **kwargs: captured.update(kwargs))
    monkeypatch.setattr(run_module, "import_module", lambda name: fake_uvicorn)
    args = create_parser().parse_args(["run", "app:app", *argv])
    console = SimpleNamespace(info=lambda message: None, error=lambda message: None)
    assert run_module.RunCommand()._run(args, console) == 0
    return captured


def test_run_passes_forwarded_allow_ips_to_uvicorn(monkeypatch):
    captured = _run_with_fake_uvicorn(monkeypatch, ["--forwarded-allow-ips", "10.0.0.0/8"])
    assert captured["forwarded_allow_ips"] == "10.0.0.0/8"


def test_run_keeps_uvicorn_proxy_default_when_flag_is_absent(monkeypatch):
    """Omitting the flag must leave uvicorn's default and FORWARDED_ALLOW_IPS untouched."""

    assert "forwarded_allow_ips" not in _run_with_fake_uvicorn(monkeypatch, [])