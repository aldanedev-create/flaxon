from __future__ import annotations

from typing import Any

from flaxon.exceptions import NotFound
from flaxon.http import JSONResponse, Request
from flaxon.modules import FlaxonModule

from .store import StoreService

catalog = FlaxonModule("catalog")
catalog.requires("store")


@catalog.get("/")
async def storefront(request: Request, store: StoreService) -> Any:
    return await request.render(
        "store.html",
        {
            "title": "Module Store",
            "products": store.list_products(),
        },
    )


@catalog.get("/api/products")
async def list_products(store: StoreService) -> JSONResponse:
    return JSONResponse({"products": store.list_products()})


@catalog.get("/api/products/<int:product_id>")
async def get_product(product_id: int, store: StoreService) -> JSONResponse:
    product = next((item for item in store.list_products() if item["id"] == product_id), None)
    if product is None:
        raise NotFound("Product does not exist.")
    return JSONResponse(product)
