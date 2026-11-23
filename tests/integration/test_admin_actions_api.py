"""Integration tests: class-based actions through the real admin HTTP surface.

Covers the acceptance criteria: approve-orders and export-CSV work end to end,
unauthorized users get 403 with no side effects, failures are reported per record,
bulk size is capped by config, actions are CSRF protected, and every run writes a
full audit-log entry.
"""

from __future__ import annotations

import csv
import io
from typing import ClassVar
from urllib.parse import urlencode

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard, AdminStore
from flaxon.admin.actions import Action, ActionResult, ApproveOrders, ExportCsv, Prompt
from flaxon.admin.registry import Registry
from flaxon.testing import TestClient


class Order:
    """Minimal in-memory model; mutation proves the action had real side effects."""

    records: ClassVar[dict] = {
        "1": {"id": "1", "reference": "ORD-1", "status": "pending", "amount": 10},
        "2": {"id": "2", "reference": "ORD-2", "status": "pending", "amount": 20},
        "3": {"id": "3", "reference": "ORD-3", "status": "paid", "amount": 30},
    }

    @classmethod
    def get_instances(cls):
        return list(cls.records.values())

    @classmethod
    def get_instance(cls, identifier):
        return cls.records.get(identifier)


@pytest.fixture
def setup(tmp_path):
    def build(*, permissions, config=None, actions=None):
        Order.records = {
            "1": {"id": "1", "reference": "ORD-1", "status": "pending", "amount": 10},
            "2": {"id": "2", "reference": "ORD-2", "status": "pending", "amount": 20},
            "3": {"id": "3", "reference": "ORD-3", "status": "paid", "amount": 30},
        }
        app = Flaxon("actions-test", debug=True)
        store = AdminStore(str(tmp_path / "admin.sqlite3"))
        dashboard = AdminDashboard(
            app,
            registry=Registry(),
            store=store,
            config=config or AdminConfig(),
            strict_permissions=True,
            microservices=False,
            users=[
                {
                    "username": "admin",
                    "password": "Admin123!",
                    "permissions": list(permissions),
                }
            ],
        )
        dashboard.register(Order, fields=["id", "reference", "status", "amount"])
        for action in actions or []:
            dashboard.register_action(action, model=Order)
        token = __import__("asyncio").run(dashboard.auth.login("admin", "Admin123!"))
        headers = {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}
        return dashboard, TestClient(app), headers

    return build


ALL = [
    "admin.superuser",
    "order.view_order",
    "order.change_order",
    "order.approve_orders_order",
    "order.export_csv_order",
]


def _post(client, url, headers, data):
    body = urlencode(data, doseq=True)
    return client.post(
        url,
        content=body,
        headers={**headers, "content-type": "application/x-www-form-urlencoded"},
    )


def test_approve_orders_end_to_end_with_audit(setup):
    dashboard, client, headers = setup(permissions=ALL, actions=[ApproveOrders()])
    response = _post(
        client,
        "/admin/order/actions/approve_orders",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1", "2"]},
    )
    assert response.status_code in {200, 302}
    assert Order.records["1"]["status"] == "approved"
    assert Order.records["2"]["status"] == "approved"
    assert Order.records["3"]["status"] == "paid"  # untouched
    entries = dashboard.store.get("audit", "entries", []) or []
    # record_activity stores its kwargs under details["details"] in the hash-chained log.
    assert any(
        e.get("action") == "action" and e["details"]["details"]["action"] == "approve_orders" for e in entries
    )


def test_export_csv_end_to_end_download(setup):
    dashboard, client, headers = setup(permissions=ALL, actions=[ExportCsv()])
    response = _post(
        client,
        "/admin/order/actions/export_csv",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1", "2"]},
    )
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert {"id", "reference", "status", "amount"}.issubset(rows[0].keys())


def test_unauthorized_action_is_403_with_no_side_effects(setup):
    dashboard, client, headers = setup(permissions=["admin.view_dashboard"], actions=[ApproveOrders()])
    response = _post(
        client,
        "/admin/order/actions/approve_orders",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1"]},
    )
    assert response.status_code == 403
    assert Order.records["1"]["status"] == "pending"
    entries = dashboard.store.get("audit", "entries", []) or []
    assert not any(e["details"].get("details", {}).get("action") == "approve_orders" for e in entries)


def test_can_run_denial_is_403_with_no_side_effects(setup):
    class Locked(ApproveOrders):
        name = "locked"
        permission = "order.approve_orders_order"

        async def can_run(self, user, dashboard, **kwargs):
            return False

    dashboard, client, headers = setup(permissions=ALL, actions=[Locked()])
    response = _post(
        client,
        "/admin/order/actions/locked",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1"]},
    )
    assert response.status_code == 403
    assert Order.records["1"]["status"] == "pending"


def test_per_record_failures_are_reported(setup):
    dashboard, client, headers = setup(permissions=ALL, actions=[ApproveOrders()])
    response = _post(
        client,
        "/admin/order/actions/approve_orders",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1", "missing"]},
    )
    assert response.status_code in {200, 302}
    assert Order.records["1"]["status"] == "approved"
    entries = dashboard.store.get("audit", "entries", []) or []
    entry = next(e for e in entries if e["details"].get("details", {}).get("action") == "approve_orders")
    assert entry["details"]["details"]["failures"] >= 1


def test_bulk_cap_from_config_is_enforced(setup):
    dashboard, client, headers = setup(
        permissions=ALL,
        config=AdminConfig(action_bulk_limit=2),
        actions=[ApproveOrders()],
    )
    response = _post(
        client,
        "/admin/order/actions/approve_orders",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1", "2", "3"]},
    )
    assert response.status_code == 400
    assert Order.records["1"]["status"] == "pending"  # nothing ran


def test_missing_csrf_is_rejected(setup):
    _, client, headers = setup(permissions=ALL, actions=[ApproveOrders()])
    response = _post(
        client,
        "/admin/order/actions/approve_orders",
        {"cookie": headers["cookie"]},
        {"ids": ["1"]},
    )
    assert response.status_code == 403
    assert Order.records["1"]["status"] == "pending"


def test_prompt_validation_rejects_bad_input(setup):
    class Prompted(Action):
        name = "prompted"
        prompts: ClassVar[list] = [Prompt("mode", choices=("fast", "slow"), required=True)]

        async def handle(self, ids, params, context):
            return ActionResult.ok("ran")

    dashboard, client, headers = setup(permissions=ALL, actions=[Prompted()])
    response = _post(
        client,
        "/admin/order/actions/prompted",
        headers,
        {"_csrf": dashboard.csrf_token(), "ids": ["1"], "mode": "bogus"},
    )
    assert response.status_code == 400
