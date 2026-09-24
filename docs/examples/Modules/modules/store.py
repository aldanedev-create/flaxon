from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class StoreService:
    """Application service shared by the catalog and order modules.

    The example uses memory so it runs with no database setup. In production,
    keep this interface and replace the lists with a repository or adapter.
    """

    products: list[dict[str, Any]] = field(default_factory=lambda: [
        {"id": 1, "name": "Flaxon Starter Kit", "price": 29.0},
        {"id": 2, "name": "Production Support", "price": 99.0},
    ])
    orders: list[dict[str, Any]] = field(default_factory=list)

    def list_products(self) -> list[dict[str, Any]]:
        return [dict(product) for product in self.products]

    def create_order(self, product_id: int, quantity: int, customer_email: str) -> dict[str, Any]:
        product = next((item for item in self.products if item["id"] == product_id), None)
        if product is None:
            raise ValueError("Product does not exist.")

        order = {
            "id": len(self.orders) + 1,
            "product_id": product_id,
            "product_name": product["name"],
            "quantity": quantity,
            "customer_email": customer_email,
            "total": round(product["price"] * quantity, 2),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.orders.append(order)
        return dict(order)

    def list_orders(self) -> list[dict[str, Any]]:
        return [dict(order) for order in self.orders]
