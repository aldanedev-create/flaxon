"""A small documented inventory API.

Run from the repository root:

    flaxon run examples.openapi_app.app:app --reload
"""

from flaxon import Flaxon, Query
from flaxon.validation import IntField, Schema, StrField


class Product(Schema):
    name = StrField(required=True, min_length=2, max_length=120)
    stock = IntField(required=True, minimum=0)


app = Flaxon(
    "inventory-api",
    openapi={
        "title": "Inventory API",
        "version": "1.0.0",
        "description": "A documented inventory service.",
    },
)


@app.get("/products", summary="List products", tags=["products"])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=100),
) -> list[Product]:
    return []


@app.post(
    "/products",
    summary="Create a product",
    tags=["products"],
    responses={201: (Product, "Product created")},
)
async def create_product(product: Product) -> Product:
    return product
