"""Run the rating extension against a real Flaxon admin.

    cd examples/flaxon_admin_rating
    python -m pip install -e .
    python -m flaxon run app:app --port 8000

Sign in at http://127.0.0.1:8000/admin/login with ``admin`` / ``Admin123!``.
The Products model uses ``RatingField``; the dashboard shows the average-rating
card and the "Rating insights" tool, both contributed by the installed
``flaxon-admin-rating`` package (no import in this file).
"""

from __future__ import annotations

from pathlib import Path

from tortoise import Tortoise, fields
from tortoise.models import Model

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.resources import Resource, Text

from flaxon_admin_rating import RatingField

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


class Product(Model):
    """A small catalog row with a 1-5 star rating."""

    name = fields.CharField(max_length=120)
    category = fields.CharField(max_length=60, default="General")
    rating = fields.IntField(default=0)

    class Meta:
        app = "models"
        table = "demo_product"


class ProductResource(Resource):
    """A model becomes a full admin, including the custom rating control."""

    model = Product
    fields = [
        Text("name").searchable().sortable(),
        Text("category").filterable(),
        RatingField("rating").sortable(),
    ]


app = Flaxon("rating-demo")
admin = AdminDashboard(
    app,
    config=AdminConfig(site_title="Rating demo", site_header="Catalog"),
    storage_path=str(DATA / "admin.sqlite3"),
    upload_dir=str(DATA / "uploads"),
    users=[
        {
            "username": "admin",
            "password": "Admin123!",
            "permissions": ["admin.superuser"],
        }
    ],
)
admin.register(ProductResource)


async def prepare_database() -> None:
    """Create the SQLite schema and seed a few rated products once."""
    await Tortoise.init(
        db_url=f"sqlite://{DATA / 'demo.sqlite3'}",
        modules={"models": ["app"]},
        # Uvicorn serves each request in its own task; the fallback keeps the
        # demo's single-process SQLite connection reachable from all of them.
        _enable_global_fallback=True,
    )
    await Tortoise.generate_schemas()
    if await Product.all().count() == 0:
        for name, category, rating in (
            ("Espresso beans", "Coffee", 5),
            ("Ceramic mug", "Kitchen", 4),
            ("Pour-over kettle", "Kitchen", 5),
            ("Paper filters", "Kitchen", 3),
            ("Cold brew bottle", "Coffee", 4),
        ):
            await Product.create(name=name, category=category, rating=rating)


app.on_startup(prepare_database)
