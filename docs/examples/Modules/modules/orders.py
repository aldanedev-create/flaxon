from __future__ import annotations

from flaxon.exceptions import BadRequest
from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule
from flaxon.validation import Schema, fields

from .store import StoreService

orders = FlaxonModule("orders")
orders.requires("store")


class CreateOrder(Schema):
    product_id = fields.IntField(required=True, minimum=1)
    quantity = fields.IntField(required=True, minimum=1, maximum=100)
    customer_email = fields.EmailField(required=True)


@orders.get("/")
async def list_orders(store: StoreService) -> JSONResponse:
    return JSONResponse({"orders": store.list_orders()})


@orders.post("/")
async def create_order(data: CreateOrder, store: StoreService) -> JSONResponse:
    try:
        order = store.create_order(
            product_id=data.product_id,
            quantity=data.quantity,
            customer_email=data.customer_email,
        )
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    return JSONResponse(order, status_code=201)
