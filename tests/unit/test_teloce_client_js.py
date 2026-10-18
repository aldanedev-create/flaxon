"""Run the Node unit tests of the Teloce debug client when Node is available."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests" / "js"


def test_teloce_client_unit_tests_pass():
    """`hintFor` and `safeEditorUrl` are pure, so Node can check them without a browser."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is not installed")
    result = subprocess.run(
        [node, "--test", str(TESTS / "teloce-client.test.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
