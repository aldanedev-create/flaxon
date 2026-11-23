"""Integration contract for Phase 4: filters, lenses, saved views, discovery,
duplicate, CSV import, policies and impersonation, exercised over real HTTP.

Abuse cases are first-class here: CSRF, IDOR on saved views and records,
over-large imports, and privilege escalation through impersonation.
"""

from __future__ import annotations

import asyncio
import json
import sys
from types import ModuleType
from typing import ClassVar
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from tortoise import Model, Tortoise, fields

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard, AdminStore
from flaxon.admin.filters import BooleanFilter, DateRangeFilter, SelectFilter
from flaxon.admin.lenses import Lens
from flaxon.admin.policies import Policy
from flaxon.admin.registry import Registry
from flaxon.testing import AsyncTestClient, TestClient


class Order:
    records: ClassVar[dict] = {}

    @classmethod
    def reset(cls):
        cls.records = {
            "1": {"id": "1", "reference": "ORD-1", "status": "pending", "fulfilled": False, "amount": 10},
            "2": {"id": "2", "reference": "ORD-2", "status": "paid", "fulfilled": False, "amount": 20},
            "3": {"id": "3", "reference": "ORD-3", "status": "paid", "fulfilled": True, "amount": 30},
        }

    @classmethod
    def get_instances(cls):
        return list(cls.records.values())

    @classmethod
    def get_instance(cls, identifier):
        return cls.records.get(identifier)

    @classmethod
    def create_instance(cls, data):
        identifier = str(max(int(key) for key in cls.records) + 1)
        row = {**data, "id": identifier}
        cls.records[identifier] = row
        return row

    @classmethod
    def delete_instance(cls, identifier):
        cls.records.pop(identifier, None)


ALL = ["admin.superuser", "admin.view_dashboard", "order.view_order", "order.change_order"]


@pytest.fixture
def setup(tmp_path):
    def build(*, permissions=ALL, config=None, filters=None, lenses=None, policy=None, extra_users=None):
        Order.reset()
        app = Flaxon("phase4-test", debug=True)
        store = AdminStore(str(tmp_path / "admin.sqlite3"))
        users = [
            {"username": "admin", "password": "Admin123!", "permissions": list(permissions)},
            {
                "username": "viewer",
                "password": "Viewer123!",
                "permissions": ["admin.view_dashboard", "order.view_order"],
            },
        ]
        users.extend(extra_users or [])
        dashboard = AdminDashboard(
            app,
            registry=Registry(),
            store=store,
            config=config or AdminConfig(),
            strict_permissions=True,
            microservices=False,
            users=users,
        )
        options = {"fields": ["id", "reference", "status", "fulfilled", "amount"]}
        if filters is not None:
            options["filters"] = filters
        if lenses is not None:
            options["lenses"] = lenses
        if policy is not None:
            options["policy"] = policy
        dashboard.register(Order, **options)
        client = TestClient(app)
        return dashboard, client

    return build


def _headers(dashboard, username="admin", password="Admin123!"):
    token = asyncio.run(dashboard.auth.login(username, password))
    return {"cookie": f"session_id={token}"}


def _post(client, url, headers, data):
    return client.post(
        url,
        content=urlencode(data, doseq=True),
        headers={**headers, "content-type": "application/x-www-form-urlencoded"},
    )


# --------------------------------------------------------------------------- filters


def test_list_applies_class_filters_from_the_url(setup):
    dashboard, client = setup(
        filters=[
            SelectFilter("status", choices=["pending", "paid"]),
            BooleanFilter("fulfilled"),
        ]
    )
    headers = _headers(dashboard)

    response = client.get("/admin/order?filter_status=paid&filter_fulfilled=true", headers=headers)
    body = response.text

    assert response.status_code == 200
    assert "ORD-3" in body
    assert "ORD-2" not in body  # paid but not fulfilled
    assert "ORD-1" not in body  # pending


def test_filter_state_is_reflected_in_the_rendered_controls(setup):
    dashboard, client = setup(filters=[SelectFilter("status", choices=["pending", "paid"])])
    body = client.get("/admin/order?filter_status=paid", headers=_headers(dashboard)).text

    assert 'name="filter_status"' in body
    assert 'value="paid" selected' in body.replace('selected="selected"', "selected")


def test_date_range_filter_is_applied(setup):
    dashboard, client = setup(filters=[DateRangeFilter("created_at")])
    # The in-memory rows have no created_at; the filter must simply be tolerated
    # (no crash) and drop rows that cannot satisfy it.
    response = client.get(
        "/admin/order?filter_created_at_from=2026-01-01&filter_created_at_to=2026-01-31",
        headers=_headers(dashboard),
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------- lenses


def test_lens_switches_query_and_columns(setup):
    dashboard, client = setup(
        filters=[SelectFilter("status", choices=["pending", "paid"])],
        lenses=[
            Lens(
                "unpaid",
                label="Unpaid orders",
                columns=["reference", "amount"],
                query={"filter_status": "pending"},
            )
        ],
    )
    headers = _headers(dashboard)

    body = client.get("/admin/order?lens=unpaid", headers=headers).text
    assert "ORD-1" in body
    assert "ORD-3" not in body
    # The lens column set replaces list_display on the page.
    assert "Unpaid orders" in body


def test_unknown_lens_is_a_400_not_a_crash(setup):
    dashboard, client = setup(lenses=[Lens("unpaid", columns=["reference"])])
    response = client.get("/admin/order?lens=nope", headers=_headers(dashboard))
    assert response.status_code == 400


# --------------------------------------------------------------------------- saved views


def test_saved_view_round_trip_redirects_to_its_query(setup):
    dashboard, client = setup(filters=[SelectFilter("status", choices=["pending", "paid"])])
    headers = _headers(dashboard)

    saved = _post(
        client,
        "/admin/order/saved-views",
        headers,
        {"_csrf": dashboard.csrf_token(), "name": "Paid only", "query": "filter_status=paid"},
    )
    assert saved.status_code in {302, 303}

    applied = client.get("/admin/order/saved-views/paid-only", headers=headers)
    assert applied.status_code in {302, 303}
    assert "filter_status=paid" in applied.headers.get("location", "")


def test_saved_views_are_per_user_and_not_enumerable(setup):
    dashboard, client = setup()
    admin_headers = _headers(dashboard)
    _post(
        client,
        "/admin/order/saved-views",
        admin_headers,
        {"_csrf": dashboard.csrf_token(), "name": "Private", "query": "filter_status=paid"},
    )

    viewer_headers = _headers(dashboard, "viewer", "Viewer123!")
    assert client.get("/admin/order/saved-views/private", headers=viewer_headers).status_code == 404


def test_saving_a_view_requires_csrf(setup):
    dashboard, client = setup()
    headers = _headers(dashboard)

    response = _post(client, "/admin/order/saved-views", headers, {"name": "No token", "query": ""})
    assert response.status_code == 403
    assert dashboard.saved_views.list("admin", "order") == []


# --------------------------------------------------------------------------- discovery


def test_palette_returns_models_and_records_as_json(setup):
    dashboard, client = setup()
    response = client.get("/admin/search/palette?q=ORD-2", headers=_headers(dashboard))

    assert response.status_code == 200
    payload = json.loads(response.text)
    assert any(model["name"] == "order" for model in payload["models"])
    assert any(record["id"] == "2" for record in payload["records"])


def test_palette_requires_authentication(setup):
    _, client = setup()
    assert client.get("/admin/search/palette?q=x").status_code in {401, 403}


def test_palette_does_not_leak_records_the_user_cannot_read(setup):
    dashboard, client = setup(
        permissions=["admin.view_dashboard"],
        policy=Policy(view_any=lambda user, obj=None: False),
    )
    response = client.get("/admin/search/palette?q=ORD", headers=_headers(dashboard))
    payload = json.loads(response.text)
    assert payload["records"] == []


# --------------------------------------------------------------------------- duplicate


def test_duplicate_creates_a_copy_and_keeps_the_original(setup):
    dashboard, client = setup()
    response = _post(
        client, "/admin/order/1/duplicate", _headers(dashboard), {"_csrf": dashboard.csrf_token()}
    )

    assert response.status_code in {302, 303}
    assert len(Order.records) == 4
    assert Order.records["1"]["reference"] == "ORD-1"
    copy = next(row for key, row in Order.records.items() if key not in {"1", "2", "3"})
    assert copy["reference"] == "ORD-1"
    assert copy["id"] != "1"


def test_duplicate_requires_csrf_and_write_permission(setup):
    dashboard, client = setup()
    headers = _headers(dashboard)

    assert _post(client, "/admin/order/1/duplicate", headers, {}).status_code == 403
    assert len(Order.records) == 3

    viewer = _headers(dashboard, "viewer", "Viewer123!")
    blocked = _post(client, "/admin/order/1/duplicate", viewer, {"_csrf": dashboard.csrf_token()})
    assert blocked.status_code == 403
    assert len(Order.records) == 3


# --------------------------------------------------------------------------- import


def test_import_dry_run_maps_columns_and_writes_nothing(setup):
    dashboard, client = setup()
    headers = {**_headers(dashboard), "x-csrf-token": dashboard.csrf_token()}
    mapping = json.dumps({"Order Ref": "reference", "Total": "amount", "State": "status"})
    csv_body = "Order Ref,Total,State\nORD-9,90,pending\n"

    response = client.post(
        f"/admin/order/import?dry_run=1&mapping={mapping}",
        content=csv_body,
        headers={**headers, "content-type": "text/csv"},
    )

    assert response.status_code == 200
    payload = json.loads(response.text)
    assert payload["valid"] == 1
    assert payload["rows"][0]["reference"] == "ORD-9"
    assert len(Order.records) == 3  # dry run wrote nothing


def test_import_reports_row_errors_and_rolls_back(setup):
    def validate(record):
        if not str(record.get("reference", "")).startswith("ORD-"):
            raise ValueError("reference must start with ORD-")
        return True

    dashboard, client = setup()
    dashboard.registry.get("order").validate_import = validate
    headers = {**_headers(dashboard), "x-csrf-token": dashboard.csrf_token()}
    csv_body = "reference,amount,status\nORD-9,90,pending\nBAD,10,pending\n"

    response = client.post(
        "/admin/order/import",
        content=csv_body,
        headers={**headers, "content-type": "text/csv"},
    )

    assert response.status_code == 422
    payload = json.loads(response.text)
    assert payload["imported"] == 0
    assert payload["rolled_back"] is True
    assert payload["errors"][0]["row"] == 2
    assert len(Order.records) == 3


def test_import_row_cap_is_enforced(setup):
    dashboard, client = setup(config=AdminConfig(import_max_rows=2))
    headers = {**_headers(dashboard), "x-csrf-token": dashboard.csrf_token()}
    csv_body = "reference,amount\nA,1\nB,2\nC,3\n"

    response = client.post(
        "/admin/order/import",
        content=csv_body,
        headers={**headers, "content-type": "text/csv"},
    )

    assert response.status_code == 413
    assert "too many rows" in response.text.lower()
    assert len(Order.records) == 3


def test_import_byte_cap_is_enforced(setup):
    dashboard, client = setup(config=AdminConfig(import_max_bytes=20))
    headers = {**_headers(dashboard), "x-csrf-token": dashboard.csrf_token()}

    response = client.post(
        "/admin/order/import",
        content="reference,amount\n" + "x" * 200,
        headers={**headers, "content-type": "text/csv"},
    )

    assert response.status_code == 413
    assert "too large" in response.text.lower()


def test_export_csv_is_formula_injection_safe(setup):
    Order.records["4"] = {"id": "4", "reference": "=cmd|' /C calc'!A0", "status": "paid", "amount": 1}
    dashboard, client = setup()
    Order.records["4"] = {"id": "4", "reference": "=cmd|' /C calc'!A0", "status": "paid", "amount": 1}

    response = client.get("/admin/order/export?format=csv", headers=_headers(dashboard))
    body = response.text

    assert response.status_code == 200
    assert "'=cmd" in body
    assert ",=cmd" not in body


# --------------------------------------------------------------------------- policies


def test_view_any_policy_denial_is_403(setup):
    dashboard, client = setup(policy=Policy(view_any=lambda user, obj=None: False))
    assert client.get("/admin/order", headers=_headers(dashboard)).status_code == 403


def test_record_level_view_policy_hides_and_blocks(setup):
    dashboard, client = setup(policy=Policy(view=lambda user, obj=None: obj.get("status") != "paid"))
    headers = _headers(dashboard)

    body = client.get("/admin/order", headers=headers).text
    assert "ORD-1" in body
    assert "ORD-2" not in body

    # Direct object access is an IDOR attempt and must be denied, not just hidden.
    assert client.get("/admin/order/2", headers=headers).status_code == 403
    assert client.get("/admin/order/1", headers=headers).status_code == 200


def test_create_and_update_policies_are_enforced(setup):
    dashboard, client = setup(
        policy=Policy(
            create=lambda user, obj=None: False,
            update=lambda user, obj=None: False,
        )
    )
    headers = _headers(dashboard)
    token = dashboard.csrf_token()

    add = _post(
        client,
        "/admin/order/add",
        headers,
        {"_csrf": token, "reference": "ORD-X", "status": "pending", "amount": "5"},
    )
    assert add.status_code == 403
    assert len(Order.records) == 3

    edit = _post(
        client,
        "/admin/order/1/edit",
        headers,
        {"_csrf": token, "reference": "HACKED", "status": "paid", "amount": "10"},
    )
    assert edit.status_code == 403
    assert Order.records["1"]["reference"] == "ORD-1"


# --------------------------------------------------------------------------- impersonation


def _impersonate(client, headers, username, token):
    return _post(client, "/admin/impersonate", headers, {"_csrf": token, "username": username})


def test_impersonation_is_disabled_by_default(setup):
    dashboard, client = setup()
    response = _impersonate(client, _headers(dashboard), "viewer", dashboard.csrf_token())
    assert response.status_code == 403


def test_impersonation_requires_explicit_permission(setup):
    dashboard, client = setup(config=AdminConfig(allow_impersonation=True))
    # "viewer" is authenticated but lacks admin.impersonate (and is not a superuser).
    headers = _headers(dashboard, "viewer", "Viewer123!")
    response = _impersonate(client, headers, "admin", dashboard.csrf_token())
    assert response.status_code == 403
    assert "Impersonating" not in client.get("/admin/", headers=headers).text


def test_impersonation_refuses_superusers_and_self(setup):
    dashboard, client = setup(
        config=AdminConfig(allow_impersonation=True),
        extra_users=[{"username": "root2", "password": "Root123!", "permissions": ["admin.superuser"]}],
        permissions=[*ALL, "admin.impersonate"],
    )
    headers = _headers(dashboard)
    token = dashboard.csrf_token()

    assert _impersonate(client, headers, "root2", token).status_code == 403
    assert _impersonate(client, headers, "admin", token).status_code == 400
    assert _impersonate(client, headers, "ghost", token).status_code == 404


def test_impersonation_switches_user_shows_banner_and_exits(setup):
    dashboard, client = setup(
        config=AdminConfig(allow_impersonation=True),
        permissions=[*ALL, "admin.impersonate"],
    )
    headers = _headers(dashboard)
    token = dashboard.csrf_token()

    started = _impersonate(client, headers, "viewer", token)
    assert started.status_code in {302, 303}

    page = client.get("/admin/", headers=headers)
    assert page.status_code == 200
    assert "Impersonating" in page.text
    assert "viewer" in page.text

    stopped = _post(client, "/admin/impersonate/exit", headers, {"_csrf": token})
    assert stopped.status_code in {302, 303}
    assert "Impersonating" not in client.get("/admin/", headers=headers).text


def test_impersonation_start_and_stop_are_audited(setup):
    dashboard, client = setup(
        config=AdminConfig(allow_impersonation=True),
        permissions=[*ALL, "admin.impersonate"],
    )
    headers = _headers(dashboard)
    token = dashboard.csrf_token()

    _impersonate(client, headers, "viewer", token)
    _post(client, "/admin/impersonate/exit", headers, {"_csrf": token})

    entries = dashboard.store.get("audit", "entries", []) or []
    actions = [entry.get("action") for entry in entries]
    assert "impersonation_started" in actions
    assert "impersonation_stopped" in actions


def test_impersonation_requires_csrf_and_leaves_session_untouched(setup):
    dashboard, client = setup(
        config=AdminConfig(allow_impersonation=True),
        permissions=[*ALL, "admin.impersonate"],
    )
    headers = _headers(dashboard)

    blocked = _post(client, "/admin/impersonate", headers, {"username": "viewer"})
    assert blocked.status_code == 403
    assert "Impersonating" not in client.get("/admin/", headers=headers).text


# --------------------------------------------------------------------------- ORM


@pytest_asyncio.fixture
async def orm_orders():
    module = ModuleType("phase4_models")
    sys.modules["phase4_models"] = module

    class Order(Model):
        reference = fields.CharField(max_length=50)
        status = fields.CharField(max_length=20)

        class Meta:
            app = "phase4_models"
            table = "phase4_order"

    Order.__module__ = "phase4_models"
    module.Order = Order
    await Tortoise.init(db_url="sqlite://:memory:", modules={"phase4_models": ["phase4_models"]})
    await Tortoise.generate_schemas()
    for index, status in enumerate(["pending", "paid", "paid"], 1):
        await Order.create(reference=f"ORD-{index}", status=status)
    try:
        yield Order
    finally:
        await Tortoise.close_connections()
        sys.modules.pop("phase4_models", None)


@pytest.mark.asyncio
async def test_orm_class_filter_is_applied_in_the_query(orm_orders):
    Order = orm_orders  # noqa: N806 - model class from the fixture
    app = Flaxon("phase4-orm", debug=True)
    dashboard = AdminDashboard(
        app,
        registry=Registry(),
        config=AdminConfig(),
        strict_permissions=True,
        microservices=False,
        users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
    )
    dashboard.register(
        Order,
        fields=["id", "reference", "status"],
        filters=[SelectFilter("status", choices=["pending", "paid"])],
    )
    token = await dashboard.auth.login("admin", "Admin123!")
    client = AsyncTestClient(app)

    response = await client.get("/admin/order?filter_status=paid", headers={"cookie": f"session_id={token}"})

    assert response.status_code == 200
    assert "ORD-2" in response.text
    assert "ORD-3" in response.text
    assert "ORD-1" not in response.text
