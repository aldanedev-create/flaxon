from __future__ import annotations

import asyncio

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.testing import TestClient


def test_admin_remember_cookie_and_profile_workspace(tmp_path):
    app = Flaxon("profile-cookie")
    dashboard = AdminDashboard(
        app,
        storage_path=str(tmp_path / "admin.sqlite3"),
        users=[{"username": "admin", "password": "Admin123!", "email": "admin@example.com", "roles": ["administrator"]}],
    )
    client = TestClient(app)
    csrf = dashboard.csrf_token()
    login = client.post(
        "/admin/login",
        content="_csrf={}&username=admin&password=Admin123%21&remember=1".format(csrf),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 302
    sessions = dashboard.store.list("sessions")
    assert len(sessions) == 1
    assert sessions[next(iter(sessions))]["expires_at"] - sessions[next(iter(sessions))]["created_at"] == 30 * 86400
    assert "set-cookie" in login.headers

    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    profile = client.get("/admin/profile", headers={"cookie": f"session_id={token}"})
    assert profile.status_code == 200
    assert "Account and security" in profile.text
    assert "Roles and capabilities" in profile.text
    assert "Cookie protection" in profile.text
