# OpenAPI, Swagger UI, and ReDoc

Flaxon generates an OpenAPI 3.1 document from the routes already registered on
your application. The generator reads path converters, endpoint annotations,
native Flaxon schemas, optional Pydantic models, query declarations,
docstrings, and route metadata. You do not maintain a second list of routes.

## Enable automatic documentation

Pass `openapi=True` when creating the application:

```python
from flaxon import Flaxon

app = Flaxon("catalog", openapi=True)
```

This registers:

| URL | Purpose |
|---|---|
| `/openapi.json` | Generated OpenAPI 3.1 document |
| `/docs` | Interactive Swagger UI with Try it out |
| `/redoc` | ReDoc reference browser |

The feature is opt-in. An application that does not pass `openapi=True` does
not expose documentation routes.

Set application metadata directly in the constructor:

```python
app = Flaxon(
    "catalog",
    openapi={
        "title": "Catalog API",
        "version": "2026.1",
        "description": "Inventory and ordering API.",
        "docs_url": "/api/docs",
        "redoc_url": "/api/reference",
        "openapi_url": "/api/openapi.json",
    },
)
```

The equivalent explicit form is useful when configuration is loaded later:

```python
app = Flaxon("catalog")
app.enable_openapi(
    title="Catalog API",
    version="2026.1",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/reference",
)
```

## Typed routes and query parameters

Path converters and `Query` declarations become OpenAPI parameters and are
also coerced and validated at runtime:

```python
from flaxon import Query


@app.get(
    "/products/<int:product_id>",
    summary="Get a product",
    tags=["products"],
    operation_id="get_product",
)
async def get_product(
    product_id: int,
    page: int = Query(1, ge=1, description="One-based result page"),
    search: str = Query("", max_length=120, description="Name search"),
):
    return {"id": product_id, "page": page, "search": search}
```

Use `Query()` without a value for a required query parameter. Use `alias` when
the public name differs from the Python argument:

```python
@app.get("/products")
async def list_products(
    page_size: int = Query(25, alias="pageSize", ge=1, le=100),
):
    return {"page_size": page_size}
```

Invalid values return Flaxon's normal `422` validation response and the same
constraints appear in the generated schema.

## Request and response schemas

Native Flaxon schemas work without an extra dependency:

```python
from flaxon.validation import IntField, Schema, StrField


class CreateProduct(Schema):
    name = StrField(required=True, min_length=2, max_length=120)
    stock = IntField(required=True, minimum=0)


@app.post(
    "/products",
    summary="Create a product",
    tags=["products"],
    responses={201: (CreateProduct, "Product created")},
)
async def create_product(product: CreateProduct) -> CreateProduct:
    return product
```

The request body and `200` response reference a reusable component schema.
The `responses` mapping accepts a description string, a schema class, a
`(schema, description)` tuple, or a raw OpenAPI response object.

Pydantic is optional. Install `flaxon[pydantic]` to use Pydantic request and
response models; their `model_json_schema()` output is copied into the
OpenAPI components section:

```python
from pydantic import BaseModel


class Product(BaseModel):
    name: str
    price: float


@app.post("/products")
async def create(product: Product) -> Product:
    return product
```

## Docstrings and metadata

The first non-empty docstring line becomes the operation summary and remaining
lines become its description. Explicit route metadata wins over the
docstring:

```python
@app.get("/reports", tags=["reporting"], deprecated=True)
async def reports() -> list[dict]:
    """List reports.

    Reports are filtered by the current user's organization.
    """
    return []
```

Every named route receives an `operationId`. Use `security` when the endpoint
requires a security scheme that your application defines:

```python
@app.get("/account", security=[{"bearerAuth": []}])
async def account():
    return {"authenticated": True}
```

OpenAPI describes the contract; it does not authenticate requests. Keep your
real authentication middleware or endpoint dependency in place.

## Modules and routers

Routes mounted with `include_router()` or `mount_module()` are discovered from
the final application registry. Metadata survives the mount, so a feature can
own its documentation next to its routes:

```python
from flaxon import Router

catalog = Router(prefix="/catalog")


@catalog.get("/products", tags=["catalog"], summary="List products")
async def products() -> list[dict]:
    return []


app.include_router(catalog, prefix="/api")
```

The generated path is `/api/catalog/products`. WebSocket routes are not added
to OpenAPI because OpenAPI describes HTTP operations; document WebSocket
messages separately with the [WebSocket guide](websockets.md).

## Protect documentation in production

Documentation is public when enabled unless you provide a guard. The guard can
be synchronous or asynchronous and may return a `Response` for a custom
denial page:

```python
from flaxon import HTTPException


async def docs_guard(request):
    if request.headers.get("x-docs-key") != "internal-preview":
        raise HTTPException(403, "Documentation is restricted.")
    return True


app.enable_openapi(
    title="Internal API",
    docs_guard=docs_guard,
    protect_docs=True,
)
```

`protect_docs=True` requires a guard so a deployment cannot accidentally claim
that its documentation is protected. The default Swagger UI does not persist
authorization tokens in browser storage. Set `persist_authorization=True` only
when that tradeoff is intentional.

For an offline or security-sensitive deployment, point `swagger_asset_url` and
`redoc_asset_url` at assets served by your own application or reverse proxy.

## Generate a checked-in specification

The CLI can generate a file for clients, SDK tooling, or CI:

```bash
flaxon docs app:app --output openapi.json
```

Use `--include-internal` only when you intentionally want framework routes
such as `/health` and `/metrics` in the exported document. In CI, fail when a
developer changed routes without updating the checked-in file:

```bash
flaxon docs app:app --output openapi.json --check
```

The check compares parsed JSON, so whitespace and indentation do not create
false failures. It reports a non-zero exit code when the file is missing,
invalid, or out of date.

## Complete copy-paste application

```python
from flaxon import Flaxon, Query
from flaxon.validation import Schema, StrField


class SearchResult(Schema):
    title = StrField(required=True)


app = Flaxon(
    "search-api",
    openapi={
        "title": "Search API",
        "version": "1.0.0",
        "description": "A small, documented Flaxon service.",
    },
)


@app.get("/search", tags=["search"])
async def search(q: str = Query("", min_length=1, max_length=80)) -> list[SearchResult]:
    return [{"title": q}]
```

Run it with:

```bash
flaxon run app:app --reload
```

Then open <http://127.0.0.1:8000/docs> or
<http://127.0.0.1:8000/redoc>.
