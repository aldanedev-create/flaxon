"""Integration contract for Teloce admin extensions on a real app and database."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import ClassVar
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from tortoise import Model, Tortoise, fields

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.resources import Field, Resource, Text
from flaxon.testing import AsyncTestClient

# The example plugin ships in the repository; putting it on sys.path exercises
# the same module an installed ``flaxon-admin-rating`` wheel provides.
PLUGIN_ROOT = str(__import__("pathlib").Path(__file__).parents[2] / "examples" / "flaxon_admin_rating")
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from flaxon_admin_rating import RatingCard, RatingExtension, RatingField  # noqa: E402


@pytest_asyncio.fixture
async def rating_app(tmp_path):
    module = ModuleType("extension_models")
    sys.modules["extension_models"] = module

    class Product(Model):
        name = fields.CharField(max_length=120)
        rating = fields.IntField(default=0)

        class Meta:
            app = "extension_models"
            table = "extension_product"

    Product.__module__ = "extension_models"
    module.Product = Product

    class ProductResource(Resource):
        model = Product
        fields: ClassVar[list[Field]] = [
            Text("name", required=True).searchable(),
            RatingField("rating", label="Rating", required=True),
        ]

    await Tortoise.init(db_url="sqlite://:memory:", modules={"extension_models": ["extension_models"]})
    await Tortoise.generate_schemas()
    for name, rating in (("Espresso", 5), ("Mug", 4), ("Kettle", 4), ("Filters", 3)):
        await Product.create(name=name, rating=rating)

    app = Flaxon("extension-test", debug=True)
    dashboard = AdminDashboard(
        app,
        config=AdminConfig(extensions=[RatingExtension()]),
        store=None,
        users=[
            {"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]},
            {
                "username": "viewer",
                "password": "Viewer123!",
                "permissions": ["product.view_product", "product.read_product"],
            },
        ],
        upload_dir=str(tmp_path / "uploads"),
    )
    dashboard.register(ProductResource)
    try:
        yield app, dashboard, Product
    finally:
        await Tortoise.close_connections()
        sys.modules.pop("extension_models", None)


async def _headers(dashboard, username="admin", password="Admin123!"):
    token = await dashboard.auth.login(username, password)
    return {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}


@pytest.mark.asyncio
async def test_dashboard_shows_extension_card_and_tool(rating_app):
    app, dashboard, _ = rating_app
    client = AsyncTestClient(app)
    response = await client.get("/admin/", headers=await _headers(dashboard))
    body = response.text
    assert response.status_code == 200
    assert "Rating insights" in body
    assert "data-extension-tool" in body
    assert "fx-rating-summary" in body
    assert "Average rating" in body
    assert "4.0" in body  # (5 + 4 + 4 + 3) / 4
    assert "4 rated records" in body


@pytest.mark.asyncio
async def test_extension_card_is_registered_once_per_model(rating_app):
    _, dashboard, _ = rating_app
    cards = [metric for metric in dashboard.metrics if isinstance(metric, RatingCard)]
    assert len(cards) == 1
    assert cards[0].placement == "dashboard"


@pytest.mark.asyncio
async def test_bundle_and_component_are_served_with_etag(rating_app):
    app, dashboard, _ = rating_app
    client = AsyncTestClient(app)
    headers = await _headers(dashboard)

    bundle = await client.get("/admin/extensions/bundle.js", headers=headers)
    assert bundle.status_code == 200
    assert bundle.headers["content-type"].startswith("application/javascript")
    assert bundle.headers["x-content-type-options"] == "nosniff"
    assert 'from "./assets/rating.js"' in bundle.text

    component = await client.get("/admin/extensions/assets/rating.js", headers=headers)
    assert component.status_code == 200
    assert "mount" in component.text
    etag = component.headers["etag"]
    cached = await client.get(
        "/admin/extensions/assets/rating.js", headers={**headers, "if-none-match": etag}
    )
    assert cached.status_code == 304
    assert cached.content == b""


@pytest.mark.asyncio
async def test_extension_assets_require_a_session(rating_app):
    app, _, _ = rating_app
    client = AsyncTestClient(app)
    assert (await client.get("/admin/extensions/bundle.js")).status_code in {302, 401, 403}
    assert (await client.get("/admin/extensions/assets/rating.js")).status_code in {302, 401, 403}


@pytest.mark.asyncio
async def test_unknown_component_is_404(rating_app):
    app, dashboard, _ = rating_app
    client = AsyncTestClient(app)
    response = await client.get("/admin/extensions/assets/missing.js", headers=await _headers(dashboard))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_extension_page_renders_from_the_database(rating_app):
    app, dashboard, _ = rating_app
    client = AsyncTestClient(app)
    response = await client.get("/admin/ratings", headers=await _headers(dashboard))
    body = response.text
    assert response.status_code == 200
    assert 'data-teloce-component="ratings"' in body
    assert "Products" in body
    assert "4.0" in body
    assert "5★ 1" in body


@pytest.mark.asyncio
async def test_extension_page_denies_users_without_the_permission(rating_app):
    app, dashboard, _ = rating_app
    client = AsyncTestClient(app)
    response = await client.get("/admin/ratings", headers=await _headers(dashboard, "viewer", "Viewer123!"))
    assert response.status_code == 403
    assert "data-teloce-component" not in response.text


@pytest.mark.asyncio
async def test_rating_field_renders_component_and_html_fallback(rating_app):
    app, dashboard, _ = rating_app
    client = AsyncTestClient(app)
    response = await client.get("/admin/product/add", headers=await _headers(dashboard))
    body = response.text
    assert response.status_code == 200
    assert 'data-teloce-component="rating"' in body
    assert "data-teloce-props=" in body
    assert 'id="field-rating"' in body
    assert '<option value="5">5 of 5</option>' in body


@pytest.mark.asyncio
async def test_rating_field_saves_and_rejects_out_of_range_values(rating_app):
    app, dashboard, Product = rating_app  # noqa: N806
    client = AsyncTestClient(app)
    headers = {**await _headers(dashboard), "content-type": "application/x-www-form-urlencoded"}
    csrf = dashboard.csrf_token()

    invalid = await client.post(
        "/admin/product/add",
        headers=headers,
        content=urlencode({"name": "Bad", "rating": "9", "_csrf": csrf}),
    )
    assert invalid.status_code == 400
    assert "rating" in invalid.text
    assert await Product.filter(name="Bad").count() == 0

    valid = await client.post(
        "/admin/product/add",
        headers=headers,
        content=urlencode({"name": "Cold brew", "rating": "4", "_csrf": csrf}),
    )
    assert valid.status_code == 302
    record = await Product.filter(name="Cold brew").first()
    assert record is not None and record.rating == 4


@pytest.mark.asyncio
async def test_rating_field_requires_csrf(rating_app):
    app, dashboard, Product = rating_app  # noqa: N806
    client = AsyncTestClient(app)
    headers = {**await _headers(dashboard), "content-type": "application/x-www-form-urlencoded"}
    response = await client.post(
        "/admin/product/add",
        headers=headers,
        content=urlencode({"name": "No token", "rating": "3"}),
    )
    assert response.status_code == 403
    assert await Product.filter(name="No token").count() == 0


@pytest.mark.asyncio
async def test_extension_content_is_escaped(rating_app):
    app, dashboard, Product = rating_app  # noqa: N806
    await Product.create(name="<script>alert(1)</script>", rating=5)
    client = AsyncTestClient(app)
    response = await client.get("/admin/product", headers=await _headers(dashboard))
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_extensions_can_be_disabled(tmp_path):
    app = Flaxon("extension-disabled", debug=True)
    dashboard = AdminDashboard(
        app,
        config=AdminConfig(enable_extensions=False, extensions=[RatingExtension()]),
        store=None,
        users=[],
        upload_dir=str(tmp_path / "uploads"),
    )
    assert dashboard.extensions.extensions == []
    assert dashboard.extension_bundle_url == ""
    assert dashboard.extensions.tools == []
