"""Legacy allowances must not allow findings in new files or new rules."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "rule, filename, expected",
    [
        ("D102", "src/flaxon/legacy.py", 0),
        ("F821", "src/flaxon/legacy.py", 1),
        ("D102", "src/flaxon/new.py", 1),
    ],
)
def test_lint_budget_enforces_each_file_and_rule(tmp_path, monkeypatch, capsys, rule, filename, expected):
    namespace = runpy.run_path(str(ROOT / "scripts/check_lint_budget.py"))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"findings": [{"file": "src/flaxon/legacy.py", "rule": "D102", "count": 1}]})
    )
    function = namespace["main"]
    function.__globals__["BASELINE"] = baseline
    result = SimpleNamespace(
        returncode=1, stdout=json.dumps([{"filename": str(ROOT / filename), "code": rule}])
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: result)
    assert function() == expected
    output = capsys.readouterr().out
    if expected:
        assert filename in output and rule in output


def test_lint_budget_propagates_tool_failure(monkeypatch, capsys):
    namespace = runpy.run_path(str(ROOT / "scripts/check_lint_budget.py"))
    monkeypatch.setattr(
        "subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=2, stderr="Invalid config")
    )
    assert namespace["main"]() == 2
    assert "Invalid config" in capsys.readouterr().err
