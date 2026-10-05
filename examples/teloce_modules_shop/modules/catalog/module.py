from pathlib import Path

from flaxon.modules import FlaxonModule


catalog = FlaxonModule(
    "catalog",
    ui_dir=Path(__file__).parent / "ui",
    ui_routes={"ProductDetails/[id].js": "/products/:id"},
)
PRODUCTS = [
    {"id": 1, "name": "Island Rose Arrangement", "price": 12500},
    {"id": 2, "name": "White Orchid Planter", "price": 18900},
]


@catalog.get("/products")
async def products():
    return {"items": PRODUCTS}


@catalog.get("/products/<product_id>")
async def product(product_id: str):
    return next((item for item in PRODUCTS if str(item["id"]) == product_id), {"error": "Not found"})
