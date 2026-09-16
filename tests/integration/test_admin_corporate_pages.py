from __future__ import annotations

import asyncio
from typing import ClassVar
from urllib.parse import urlencode

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.testing import TestClient


class CorporateRecord:
    items: ClassVar[dict[str, dict[str, str]]] = {
        "1": {"id": "1", "name": "Northwind", "description": "Primary account"},
    }

    @classmethod
    async def get_instances(cls):
        return list(cls.items.values())

    @classmethod
    async def get_instance(cls, object_id):
        return cls.items.get(str(object_id))


class EditableRecord:
    items: ClassVar[dict[str, dict[str, object]]] = {
        "1": {"id": "1", "name": "Northwind", "description": "Primary account", "active": True, "metadata": {"tier": "gold"}},
    }

    @classmethod
    async def get_instance(cls, object_id):
        return cls.items.get(str(object_id))

    @classmethod
    async def update_instance(cls, object_id, data):
        record = cls.items[str(object_id)]
        record.update(data)
        return record


def test_corporate_admin_pages_render_with_real_contexts():
    app = Flaxon("admin-corporate-pages", debug=True)
    admin = AdminDashboard(
        app,
        users=[{"username": "admin", "password": "Admin123!", "roles": ["administrator"]}],
    )
    admin.register(
        CorporateRecord,
        name="account",
        fields=["id", "name", "description"],
        list_display=["id", "name", "description"],
    )
    token = asyncio.run(admin.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": admin.csrf_token()}
    client = TestClient(app)

    pages = {
        "/admin/": "Content models",
        "/admin/operations": "Operations center",
        "/admin/roles": "Groups and permissions",
        "/admin/settings": "Admin settings",
        "/admin/users": "User administration",
        "/admin/activity": "Audit filters",
        "/admin/account/add": "Create",
        "/admin/account/1/delete": "Delete this",
        "/admin/account/1/history": "Change timeline",
    }
    for path, marker in pages.items():
        response = client.get(path, headers=headers)
        assert response.status_code == 200, path
        assert marker in response.text, path

    filtered = client.get("/admin/activity?action=created", headers=headers)
    assert filtered.status_code == 200
    assert "Apply filters" in filtered.text

    search = client.get("/admin/search?q=Northwind", headers=headers)
    assert search.status_code == 200
    assert "Northwind" in search.text
    assert "Matching records" in search.text

    missing_history = client.get("/admin/user/6a7b51f87e595ae5/history", headers=headers)
    assert missing_history.status_code == 404
    assert "The requested admin resource does not exist." in missing_history.text


def test_edit_workspace_renders_metadata_and_supports_save_modes():
    app = Flaxon("admin-edit-workspace", debug=True)
    admin = AdminDashboard(
        app,
        users=[{"username": "admin", "password": "Admin123!", "roles": ["administrator"]}],
    )
    admin.register(
        EditableRecord,
        name="account",
        fields=["id", "name", "description", "active", "metadata"],
        readonly_fields=["id"],
    )
    token = asyncio.run(admin.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}"}
    client = TestClient(app)

    page = client.get("/admin/account/1/edit", headers=headers)
    assert page.status_code == 200
    assert "Save and continue" in page.text
    assert "Save and add another" in page.text
    assert 'data-json-field' in page.text
    assert "Primary account" in page.text
    assert "Read-only" in page.text

    body = urlencode(
        {
            "_csrf": admin.csrf_token(),
            "_version": "",
            "_save": "continue",
            "id": "must-not-change",
            "name": "Updated account",
            "description": "Updated description",
            "active": "false",
            "metadata": '{"tier": "silver"}',
        }
    )
    saved = client.post(
        "/admin/account/1/edit",
        content=body,
        headers={**headers, "content-type": "application/x-www-form-urlencoded"},
    )
    assert saved.status_code == 302
    assert saved.headers["location"] == "/admin/account/1/edit"
    assert EditableRecord.items["1"]["id"] == "1"
    assert EditableRecord.items["1"]["active"] == "false"

    add_body = urlencode({"_csrf": admin.csrf_token(), "_version": "", "_save": "add", "name": "Another"})
    added = client.post(
        "/admin/account/1/edit",
        content=add_body,
        headers={**headers, "content-type": "application/x-www-form-urlencoded"},
    )
    assert added.status_code == 302
    assert added.headers["location"] == "/admin/account/add"
