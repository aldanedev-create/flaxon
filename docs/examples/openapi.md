# OpenAPI API Example

This example is a complete small API with automatic request schemas, typed
query parameters, Swagger UI, ReDoc, and a checked-in OpenAPI export.

Create `app.py`:

```python
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
```

Install and run:

```bash
python -m pip install "flaxon[standard]"
flaxon run app:app --reload
```

Open:

- <http://127.0.0.1:8000/docs> for Swagger UI.
- <http://127.0.0.1:8000/redoc> for ReDoc.
- <http://127.0.0.1:8000/openapi.json> for the raw contract.

Export the same contract for code generation or CI:

```bash
flaxon docs app:app --output openapi.json
flaxon docs app:app --output openapi.json --check
```

The framework discovers routes from the application registry, so routes in
routers and mounted modules are included automatically after they are mounted.
See the [OpenAPI guide](../guides/openapi.md) for Pydantic, security guards,
custom paths, response objects, and production asset hosting.
