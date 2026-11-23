"""Prove the example plugin installs as a real distribution and appears in Admin.

Builds a wheel, installs it into a fresh virtual environment (which still sees
the repository's editable Flaxon install through ``--system-site-packages``),
then asks that interpreter to boot an admin and render the index.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "examples" / "flaxon_admin_rating"

SCRIPT = """
import asyncio
from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.testing import TestClient

app = Flaxon("installed-extension", debug=True)
dashboard = AdminDashboard(
    app,
    store=None,
    users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
    upload_dir="/tmp/flaxon-extension-install-uploads",
)
extensions = dashboard.extensions.extensions
assert [extension.name for extension in extensions] == ["rating"], extensions
assert dashboard.extension_bundle_url == "/admin/extensions/bundle.js"
assert [tool.label for tool in dashboard.extensions.tools] == ["Rating insights"]
assert dashboard.extensions.component_names == ["rating", "rating-summary", "ratings"]

token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
response = TestClient(app).get("/admin/", headers={"cookie": f"session_id={token}"})
assert response.status_code == 200, response.status_code
assert "Rating insights" in response.text
assert "/admin/extensions/bundle.js" in response.text
print("installed extension rendered")
"""


@pytest.mark.timeout(300)
def test_example_plugin_installs_into_a_clean_venv(tmp_path):
    wheels = tmp_path / "wheels"
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(PLUGIN),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheels),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    wheel = next(wheels.glob("flaxon_admin_rating-*.whl"))

    venv = tmp_path / "venv"
    create = subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert create.returncode == 0, create.stderr
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    install = subprocess.run(
        [str(python), "-m", "pip", "install", "--no-deps", "--quiet", str(wheel)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr

    result = subprocess.run(
        [str(python), "-c", SCRIPT],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "installed extension rendered" in result.stdout
