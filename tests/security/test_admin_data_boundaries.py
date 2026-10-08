"""Search, exports, audit records, and bulk actions obey model/object boundaries."""
import asyncio
import secrets
from urllib.parse import urlencode

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.registry import Registry
from flaxon.testing import TestClient


class ConfidentialRecord:
    records = [
        {"id": "1", "name": "Visible needle", "owner": "reader", "password_hash": "must-not-appear"},
        {"id": "2", "name": "Hidden needle", "owner": "other", "password_hash": "also-private"},
    ]

    @classmethod
    async def get_instances(cls):
        return cls.records

    @classmethod
    async def get_instance(cls, identifier):
        return next(value for value in cls.records if value["id"] == identifier)


def setup(permissions):
    app = Flaxon("admin-boundaries", debug=True)
    password = secrets.token_urlsafe(20) + "Aa1!"
    dashboard = AdminDashboard(app, registry=Registry(), strict_permissions=True, microservices=False, users=[{"username": "reader", "password": password, "permissions": permissions}])
    called = []
    dashboard.register(ConfidentialRecord, fields=["id", "name", "owner"], can_view=lambda user, row: row is None or row["owner"] == user.username, can_change=lambda user, row: row is None or row["owner"] == user.username, actions={"process": lambda ids: called.extend(ids)})
    session = asyncio.run(dashboard.auth.login("reader", password))
    headers = {"cookie": f"session_id={session}", "x-csrf-token": dashboard.csrf_token()}
    return dashboard, TestClient(app), headers, called


def test_search_cannot_bypass_model_permission():
    _, client, headers, _ = setup(["admin.view_dashboard"])
    response = client.get("/admin/search?q=needle", headers=headers)
    assert response.status_code == 200
    assert "Visible needle" not in response.text
    assert "Hidden needle" not in response.text
    assert client.get("/admin/confidentialrecord/export", headers=headers).status_code == 403


def test_search_and_export_obey_object_rules_and_redact_credentials():
    _, client, headers, _ = setup(["admin.view_dashboard", "confidentialrecord.view_confidentialrecord"])
    response = client.get("/admin/search?q=needle", headers=headers)
    assert "Visible needle" in response.text
    assert "Hidden needle" not in response.text
    exported = client.get("/admin/confidentialrecord/export", headers=headers)
    assert exported.status_code == 200
    assert len(exported.json()) == 1
    assert exported.json()[0]["password_hash"] == "[redacted]"


def test_bulk_action_checks_all_objects_before_callback():
    dashboard, client, headers, called = setup(["confidentialrecord.process_confidentialrecord", "confidentialrecord.change_confidentialrecord"])
    data = urlencode({"_csrf": dashboard.csrf_token(), "ids": ["1", "2"]}, doseq=True)
    response = client.post("/admin/confidentialrecord/actions/process", content=data, headers={**headers, "content-type": "application/x-www-form-urlencoded"})
    assert response.status_code == 403
    assert called == []


def test_audit_snapshots_remove_nested_credentials():
    dashboard, _, _, _ = setup([])
    dashboard.record_activity("updated", "record", type("Request", (), {"user": None})(), before={"password_hash": "private", "metadata": {"api_key": "private", "name": "Public"}})
    details = dashboard.activities[-1].details
    assert details["before"]["password_hash"] == "[redacted]"
    assert details["before"]["metadata"]["api_key"] == "[redacted]"
    assert details["before"]["metadata"]["name"] == "Public"
