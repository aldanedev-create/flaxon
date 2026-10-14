"""Visible environment phases and recovery must never regenerate user files."""

import argparse
import subprocess
import sys
from types import SimpleNamespace

import pytest

import flaxon.cli.commands.new as module
from flaxon.cli.commands.new import NewCommand
from flaxon.cli.console import Console
from flaxon.cli.generator import Generator
from flaxon.cli.main import create_parser


def test_environment_phases_are_separate(monkeypatch, tmp_path):
    phases = []
    monkeypatch.setattr(
        NewCommand,
        "_run_step",
        lambda command, directory, console, phase, timeout: phases.append((command, phase, timeout)),
    )
    NewCommand._create_environment(tmp_path, Console(color=False), timeout=9)
    assert len(phases) == 2
    assert phases[0][0] == [sys.executable, "-u", "-m", "venv", "--without-pip", ".venv"]
    assert phases[1][0][1:] == ["-u", "-m", "ensurepip", "--upgrade"]
    assert str(tmp_path / ".venv") in phases[1][0][0]
    assert all(phase[2] == 9 for phase in phases)


def test_resume_preserves_edited_project(monkeypatch, tmp_path, capsys):
    project = tmp_path / "my project"
    Generator().generate(project)
    (project / "app.py").write_text("# User's edited application\n")
    before = {path.relative_to(project): path.read_bytes() for path in project.rglob("*") if path.is_file()}
    calls = []
    monkeypatch.setattr(NewCommand, "_create_environment", lambda *args, **kwargs: calls.append(kwargs))
    args = create_parser(include_project=False).parse_args([
        "new",
        str(project),
        "--resume-venv",
        "--venv-timeout",
        "300",
    ])
    assert NewCommand()._run(args, Console(color=False)) == 0
    assert calls == [{"timeout": 300}]
    assert before == {
        path.relative_to(project): path.read_bytes() for path in project.rglob("*") if path.is_file()
    }
    assert "management.py runserver" in capsys.readouterr().out


def test_timeout_retains_files_and_prints_recovery(monkeypatch, tmp_path, capsys):
    project = tmp_path / "demo"

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("ensurepip", 12)

    monkeypatch.setattr(NewCommand, "_create_environment", fail)
    args = create_parser(include_project=False).parse_args(["new", str(project)])
    assert NewCommand()._run(args, Console(color=False)) == 1
    output = capsys.readouterr()
    assert (project / "app.py").exists()
    assert "--resume-venv" in output.out
    assert "12 seconds" in output.err
    assert "Project setup complete" not in output.out


def test_cancel_returns_conventional_status_and_recovery(monkeypatch, tmp_path):
    def cancel(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(NewCommand, "_create_environment", cancel)
    args = create_parser(include_project=False).parse_args(["new", str(tmp_path / "demo")])
    assert NewCommand()._run(args, Console(color=False)) == 130


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_timeout_rejects_invalid_values(value):
    with pytest.raises(SystemExit):
        create_parser(include_project=False).parse_args(["new", "demo", "--venv-timeout", value])


def test_resume_rejects_unrelated_directory(tmp_path):
    args = argparse.Namespace(directory=str(tmp_path), resume_venv=True, no_venv=False)
    assert NewCommand()._run(args, Console(color=False)) == 1


def test_without_environment_does_not_launch_process(monkeypatch, tmp_path, capsys):
    def unexpected(*args, **kwargs):
        raise AssertionError("Unexpected environment setup")

    monkeypatch.setattr(NewCommand, "_create_environment", unexpected)
    args = create_parser(include_project=False).parse_args(["new", str(tmp_path / "demo"), "--no-venv"])
    assert NewCommand()._run(args, Console(color=False)) == 0
    assert "environment setup skipped" in capsys.readouterr().out


def test_windows_next_steps_need_no_activation(monkeypatch, tmp_path, capsys):

    monkeypatch.setattr(module, "os", SimpleNamespace(name="nt"))
    NewCommand._next_steps(
        tmp_path / "developer's project", Console(color=False), environment=True, fullstack=True
    )
    output = capsys.readouterr().out
    assert "Set-Location -LiteralPath" in output
    assert "developer''s project" in output
    assert ".\\.venv\\Scripts\\python.exe -m pip install -e ." in output
    assert "Activate.ps1" not in output


def test_windows_cleanup_targets_owned_process_tree(monkeypatch):

    calls = []
    process = SimpleNamespace(pid=42, poll=lambda: None, wait=lambda timeout=None: 0)
    monkeypatch.setattr(module, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command))
    NewCommand._stop_process(process)
    assert calls == [["taskkill", "/PID", "42", "/T", "/F"]]


def test_native_environment_creation_and_resume(tmp_path):
    project = tmp_path / "native project with spaces"
    args = create_parser(include_project=False).parse_args(["new", str(project)])
    assert NewCommand()._run(args, Console(color=False)) == 0
    python = project / ".venv" / ("Scripts/python.exe" if module.os.name == "nt" else "bin/python")
    subprocess.run([str(python), "-m", "pip", "--version"], check=True)
    original = (project / "app.py").read_bytes()
    args.resume_venv = True
    assert NewCommand()._run(args, Console(color=False)) == 0
    assert (project / "app.py").read_bytes() == original


def test_resume_from_active_project_environment_does_not_copy_its_python(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    monkeypatch.setattr(NewCommand, "_run_step", lambda command, *args: calls.append(command))
    NewCommand._create_environment(tmp_path, Console(color=False))
    assert len(calls) == 1
    assert calls[0][1:] == ["-u", "-m", "ensurepip", "--upgrade"]
