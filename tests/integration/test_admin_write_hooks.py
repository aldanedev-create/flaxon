"""Admin writes must fail loudly when a registered model cannot be saved.

A model only gains `create_instance`/`update_instance` when the registry wraps it
with the Tortoise adapter. Plain classes registered without the async CRUD hooks
used to be saved as a silent no-op: the browser got a 302 back to the list view
and the audit trail still recorded a "created" entry even though nothing was
written. These tests pin the explicit-failure behaviour.
"""

from __future__ import annotations

import asyncio
from typing import ClassVar
from urllib.parse import urlencode

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.testing import TestClient


class ReadOnlyRecord:
    """The shape people write first: list/detail hooks only, no write hooks."""

    items: ClassVar[dict[str, dict]] = {
        "1": {"id": "1", "title": "Northwind", "body": "Primary account"},
    }

    @classmethod
    async def get_instances(cls):
        return list(cls.items.values())

    @classmethod
    async def get_instance(cls, object_id):
        return cls.items.get(str(object_id))


class WritableRecord:
    """Same model with the write hooks Admin actually calls."""

    items: ClassVar[dict[str, dict]] = {}

    @classmethod
    async def get_instances(cls):
        return list(cls.items.values())

    @classmethod
    async def get_instance(cls, object_id):
        return cls.items.get(str(object_id))

    @classmethod
    async def create_instance(cls, data):
        pk = str(len(cls.items) + 1)
        record = {"id": pk, **{key: value for key, value in data.items() if key != "id"}}
        cls.items[pk] = record
        return record

    @classmethod
    async def update_instance(cls, object_id, data):
        record = cls.items[str(object_id)]
        record.update(data)
        return record


def build_dashboard():
    """Build a dashboard with one unwritable and one writable model."""
    app = Flaxon("admin-write-hooks", debug=True)
    admin = AdminDashboard(
        app,
        users=[{"username": "admin", "password": "Admin123!", "roles": ["administrator"]}],
    )
    admin.register(
        ReadOnlyRecord,
        name="readonly",
        fields=["id", "title", "body"],
        list_display=["id", "title", "body"],
    )
    admin.register(
        WritableRecord,
        name="writable",
        fields=["id", "title", "body"],
        list_display=["id", "title", "body"],
    )
    token = asyncio.run(admin.auth.login("admin", "Admin123!"))
    headers = {
        "cookie": f"session_id={token}",
        "x-csrf-token": admin.csrf_token(),
        "content-type": "application/x-www-form-urlencoded",
    }
    return admin, TestClient(app), headers


def post(client, headers, path, payload, csrf):
    """Submit an admin form."""
    body = dict(payload)
    body["_csrf"] = csrf
    return client.post(path, content=urlencode(body), headers=headers)


def test_add_form_rejects_model_without_create_hook():
    admin, client, headers = build_dashboard()
    before = dict(ReadOnlyRecord.items)

    response = post(
        client, headers, "/admin/readonly/add", {"title": "Hello", "body": "World"}, admin.csrf_token()
    )

    # Not a 302 back to the list view: the save has to fail loudly.
    assert response.status_code == 400, response.headers.get("location", "")
    assert "create_instance" in response.text
    # Nothing was written, and the audit trail does not claim otherwise.
    assert ReadOnlyRecord.items == before
    assert [activity.action for activity in admin.activities] == []


def test_edit_form_rejects_model_without_update_hook():
    admin, client, headers = build_dashboard()
    before = dict(ReadOnlyRecord.items["1"])

    response = post(
        client, headers, "/admin/readonly/1/edit", {"title": "Changed", "body": "Changed"}, admin.csrf_token()
    )

    assert response.status_code == 400, response.headers.get("location", "")
    assert "update_instance" in response.text
    assert ReadOnlyRecord.items["1"] == before
    assert [activity.action for activity in admin.activities] == []


def test_add_form_saves_when_create_hook_exists():
    admin, client, headers = build_dashboard()
    WritableRecord.items.clear()

    response = post(
        client, headers, "/admin/writable/add", {"title": "Hello", "body": "World"}, admin.csrf_token()
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/admin/writable"
    assert WritableRecord.items == {"1": {"id": "1", "title": "Hello", "body": "World"}}
    assert [activity.action for activity in admin.activities] == ["created"]


def test_edit_form_saves_when_update_hook_exists():
    admin, client, headers = build_dashboard()
    WritableRecord.items.clear()
    WritableRecord.items["1"] = {"id": "1", "title": "Before", "body": "Before"}

    response = post(
        client, headers, "/admin/writable/1/edit", {"title": "After", "body": "After"}, admin.csrf_token()
    )

    assert response.status_code == 302
    assert WritableRecord.items["1"] == {"id": "1", "title": "After", "body": "After"}
    assert [activity.action for activity in admin.activities] == ["updated"]
