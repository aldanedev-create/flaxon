"""Integration contract for the additive declarative admin Resource API."""

from __future__ import annotations

import asyncio
import logging
import sys
from types import ModuleType
from typing import ClassVar
from urllib.parse import urlencode

import pytest
from tortoise import Model, Tortoise, fields

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.registry import Registry
from flaxon.admin.resources import BelongsTo, Field, Number, Resource, Text
from flaxon.testing import TestClient

# ---------------------------------------------------------------------------
# A model becomes a full admin in <10 lines.
# ---------------------------------------------------------------------------


def test_resource_registration_is_under_ten_lines():
    """This executable snippet is the documented minimal example (docs-as-contract)."""
    source = """
from flaxon.admin import AdminDashboard
from flaxon.admin.resources import Resource, Text, Email
class CustomerResource(Resource):
    model = Customer
    fields = [Text("name", required=True).searchable(), Email("email")]
dashboard.register(CustomerResource)
"""
    assert len([line for line in source.splitlines() if line.strip()]) <= 9
    namespace = {
        "Customer": type("Customer", (), {}),
        "AdminDashboard": AdminDashboard,
        "Resource": Resource,
        "Text": Text,
        "Email": __import__("flaxon.admin.resources", fromlist=["Email"]).Email,
    }
    dashboard = type("FakeDashboard", (), {"register": lambda self, obj: None})()
    namespace["dashboard"] = dashboard
    exec(source, namespace)
    resource = namespace["CustomerResource"]()
    assert resource.get_field("name").is_searchable is True


# ---------------------------------------------------------------------------
# Real-server validation and escaping through the admin views.
# ---------------------------------------------------------------------------


class InMemoryOrder:
    """Minimal write-capable model using the legacy hook path."""

    rows: ClassVar[dict[str, dict]] = {}

    def __init__(self, **values):
        self.__dict__.update(values)
        self.pk = values.get("id", "")

    @classmethod
    def get_instances(cls):
        return [cls(**row) for row in cls.rows.values()]

    @classmethod
    def get_instance(cls, object_id):
        row = cls.rows.get(str(object_id))
        return cls(**row) if row else None

    @classmethod
    def create_instance(cls, data):
        identifier = str(len(cls.rows) + 1)
        row = {"id": identifier, **data}
        cls.rows[identifier] = row
        return cls(**row)

    @classmethod
    def update_instance(cls, object_id, data):
        cls.rows[str(object_id)].update(data)
        return cls.get_instance(object_id)


@pytest.fixture
def resource_dashboard(tmp_path):
    InMemoryOrder.rows = {}
    app = Flaxon("resource-test", debug=True)
    registry = Registry()

    class OrderResource(Resource):
        model = InMemoryOrder
        fields: ClassVar[list[Field]] = [
            Text("reference", required=True, min_length=3).searchable().show_on_index(),
            Text("customer_email").help("A contact address").show_on_index(),
            Number("total", minimum=0).show_on_index(),
        ]

    dashboard = AdminDashboard(
        app,
        registry=registry,
        store=None,
        users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
        upload_dir=str(tmp_path / "uploads"),
    )
    dashboard.register(OrderResource)
    return app, dashboard, registry


def _auth(app, dashboard):
    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    return {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}


def test_resource_form_shows_labels_and_help_text(resource_dashboard):
    app, dashboard, _ = resource_dashboard
    client = TestClient(app)
    response = client.get("/admin/order/add", headers=_auth(app, dashboard))
    assert response.status_code == 200
    body = response.text
    assert "Customer Email" in body
    assert "A contact address" in body
    assert "aria-describedby" in body
    assert 'for="field-customer-email"' in body
    assert 'id="field-customer-email"' in body


def test_server_side_validation_blocks_invalid_resource_form(resource_dashboard):
    app, dashboard, _ = resource_dashboard
    client = TestClient(app)
    headers = {**_auth(app, dashboard), "content-type": "application/x-www-form-urlencoded"}
    response = client.post(
        "/admin/order/add",
        headers=headers,
        content=urlencode({
            "reference": "A",
            "customer_email": "not-an-email",
            "total": "-5",
            "_csrf": dashboard.csrf_token(),
        }),
    )
    assert response.status_code == 400
    assert "customer_email" in response.text
    assert InMemoryOrder.rows == {}


def test_valid_resource_form_creates_record(resource_dashboard):
    app, dashboard, _ = resource_dashboard
    client = TestClient(app)
    headers = {**_auth(app, dashboard), "content-type": "application/x-www-form-urlencoded"}
    response = client.post(
        "/admin/order/add",
        headers=headers,
        content=urlencode({
            "reference": "ORD-100",
            "customer_email": "buyer@example.com",
            "total": "42",
            "_csrf": dashboard.csrf_token(),
        }),
    )
    assert response.status_code == 302
    assert next(iter(InMemoryOrder.rows.values()))["total"] == 42


# ---------------------------------------------------------------------------
# N+1 guard: a BelongsTo column must not issue one query per row.
# ---------------------------------------------------------------------------


class QueryCounter(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.statements: list[str] = []

    def emit(self, record):
        message = record.getMessage()
        if message.lstrip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            self.statements.append(message)


@pytest.mark.asyncio
async def test_belongs_to_index_column_does_not_cause_n_plus_one():
    models = ModuleType("phase1_models")
    sys.modules["phase1_models"] = models

    class Customer(Model):
        name = fields.CharField(max_length=50)

        class Meta:
            app = "phase1_models"
            table = "phase1_customer"

    class Order(Model):
        reference = fields.CharField(max_length=50)
        customer = fields.ForeignKeyField("phase1_models.Customer", related_name="orders")

        class Meta:
            app = "phase1_models"
            table = "phase1_order"

    Customer.__module__ = "phase1_models"
    Order.__module__ = "phase1_models"
    models.Customer = Customer
    models.Order = Order

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"phase1_models": ["phase1_models"]},
    )
    await Tortoise.generate_schemas()

    try:

        class OrderResource(Resource):
            model = Order
            fields: ClassVar[list[Field]] = [
                Text("reference").show_on_index(),
                BelongsTo("customer").show_on_index(),
            ]

        registry = Registry()
        app = Flaxon("n1-test")
        dashboard = AdminDashboard(app, registry=registry, store=None, users=[], upload_dir="/tmp")
        dashboard.register(OrderResource)
        adapter = registry.get("order").model

        for index in range(5):
            customer = await Customer.create(name=f"Customer {index}")
            await Order.create(reference=f"ORD-{index}", customer=customer)

        counter = QueryCounter()
        logger = logging.getLogger("tortoise.db_client")
        logger.addHandler(counter)
        logger.setLevel(logging.DEBUG)
        try:
            result = await adapter.query(page=1, per_page=5)
            items = result["items"]
            # Touch the relation exactly as the list template does.
            labels = [str(item.customer) for item in items]
        finally:
            logger.removeHandler(counter)

        assert len(labels) == 5
        assert len(counter.statements) <= 4, (
            f"Expected a bounded number of SQL statements, got {len(counter.statements)}: "
            f"{counter.statements}"
        )
    finally:
        await Tortoise.close_connections()
