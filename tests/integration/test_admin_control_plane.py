from __future__ import annotations

import asyncio

from flaxon import Flaxon
from flaxon.admin import AdminDashboard, AdminStore, RemoteModelAdapter, ServiceRegistry
from flaxon.modules import FlaxonModule
from flaxon.testing import TestClient


def _admin(tmp_path):
    app = Flaxon("control-plane", debug=True)
    admin = AdminDashboard(
        app,
        storage_path=str(tmp_path / "admin.sqlite3"),
        users=[{"username": "root", "password": "Admin123!", "roles": ["administrator"]}],
    )
    token = asyncio.run(admin.auth.login("root", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": admin.csrf_token()}
    return app, admin, TestClient(app), headers


def test_control_plane_registers_services_and_persists_registry(tmp_path):
    app, admin, client, headers = _admin(tmp_path)
    created = client.post(
        "/admin/api/control-plane/services",
        json_data={"name": "catalog", "display_name": "Catalog", "base_url": "https://catalog.internal", "environment": "production"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["name"] == "catalog"

    instance = client.post(
        "/admin/api/control-plane/instances",
        json_data={"service": "catalog", "address": "10.0.0.12:8000", "status": "healthy"},
        headers=headers,
    )
    assert instance.status_code == 201
    assert client.get("/admin/api/control-plane/services", headers=headers).json()["services"][0]["name"] == "catalog"
    updated = client.patch("/admin/api/control-plane/services/catalog", json_data={"status": "healthy"}, headers=headers)
    assert updated.status_code == 200 and updated.json()["status"] == "healthy"
    assert client.get("/admin/services", headers=headers).status_code == 200
    assert "Catalog" in client.get("/admin/services", headers=headers).text
    assert client.get("/admin/health", headers=headers).status_code == 200
    for section in admin.control_plane.PAGE_SECTIONS:
        assert client.get(f"/admin/{section}", headers=headers).status_code == 200, section

    restored = ServiceRegistry(AdminStore(str(tmp_path / "admin.sqlite3")))
    assert restored.get("catalog")["environment"] == "production"
    assert restored.instances("catalog")[0]["status"] == "healthy"


def test_control_plane_mutations_require_csrf_and_service_tokens_are_scoped(tmp_path):
    _app, admin, client, headers = _admin(tmp_path)
    no_csrf = client.post("/admin/api/control-plane/events", json_data={"topic": "OrderCreated"}, headers={"cookie": headers["cookie"]})
    assert no_csrf.status_code == 403

    key = client.post(
        "/admin/api/control-plane/service-accounts",
        json_data={"subject": "orders", "scopes": ["orders.read"], "label": "Orders worker"},
        headers=headers,
    )
    assert key.status_code == 201
    assert key.json()["token"].startswith("fxs_")
    listing = client.get("/admin/api/control-plane/service-accounts", headers=headers).json()["items"]
    assert "token" not in listing[0]
    assert client.delete(f"/admin/api/control-plane/service-accounts/{listing[0]['token_id']}", headers=headers).json()["deleted"] is True


def test_remote_model_adapter_uses_service_contract():
    class FakeClient:
        async def get(self, path):
            return {"items": [{"id": "1", "name": "Remote"}]} if path == "/products" else {"id": "1"}

        async def post(self, path, body):
            return {"id": "2", **body}

        async def patch(self, path, body):
            return {"id": path.rsplit("/", 1)[-1], **body}

        async def delete(self, path):
            return {"deleted": True}

    adapter = RemoteModelAdapter(FakeClient(), "products")
    assert asyncio.run(adapter.get_instances())[0]["name"] == "Remote"
    assert asyncio.run(adapter.create_instance({"name": "New"}))["name"] == "New"
    assert asyncio.run(adapter.update_instance("1", {"name": "Changed"}))["id"] == "1"
    assert asyncio.run(adapter.delete_instance("1"))["deleted"] is True


def test_flaxon_module_can_extend_admin_routes(tmp_path):
    app, admin, client, headers = _admin(tmp_path)
    reports = FlaxonModule("reports")

    @reports.get("/summary")
    async def summary():
        return {"module": "reports", "ok": True}

    admin.mount_module(reports, prefix="/admin/extensions/reports")
    response = client.get("/admin/extensions/reports/summary", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"module": "reports", "ok": True}


def test_control_plane_operational_collections_are_real_persistent_records(tmp_path):
    _app_instance, admin_instance, client, headers = _admin(tmp_path)
    created = client.post("/admin/api/control-plane/flags", json_data={"name": "new-checkout", "enabled": False}, headers=headers)
    assert created.status_code == 201
    flag_id = created.json()["id"]
    assert client.get("/admin/flags", headers=headers).status_code == 200
    updated = client.patch(f"/admin/api/control-plane/flags/{flag_id}", json_data={"enabled": True}, headers=headers)
    assert updated.status_code == 200 and updated.json()["enabled"] is True
    assert client.delete(f"/admin/api/control-plane/flags/{flag_id}", headers=headers).status_code == 200
    assert client.get("/admin/api/control-plane/flags", headers=headers).json()["items"] == []
