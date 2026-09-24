# Growing a Flaxon application

This guide is for an application with roughly 200 pages, endpoints, views, or
feature screens. At that size, the important decision is not the number of
files—it is keeping each feature independent enough to change and test safely.

## Use feature modules

Keep each bounded feature together: its routes, schemas, service, templates,
and tests. Do not put business logic in route functions or create one global
`routes.py` file.

```text
myapp/
├── app/
│   ├── main.py                 # application factory and global middleware
│   ├── config.py               # environment-specific settings
│   ├── modules/
│   │   ├── accounts/
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── templates/accounts/
│   │   ├── catalog/
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── templates/catalog/
│   │   └── billing/
│   │       ├── routes.py
│   │       ├── schemas.py
│   │       └── service.py
│   └── infrastructure/
│       ├── database.py
│       ├── cache.py
│       └── logging.py
├── tests/
│   ├── modules/
│   ├── integration/
│   └── security/
└── pyproject.toml
```

This layout works just as well for 20 features as it does for 200 pages. Split
a large feature into submodules only when that feature itself becomes hard to
navigate.

## Use the same boundary for Pydantic and FastMCP

Optional integrations belong inside the feature module that uses them. The
application factory should mount modules and provide shared dependencies; it
should not contain every schema or tool.

```python
# app/modules/catalog/module.py
from typing import Any

from pydantic import BaseModel

from flaxon.modules import FlaxonModule

catalog = FlaxonModule("catalog")


class CreateProduct(BaseModel):
    name: str
    price: float


@catalog.post("/")
async def create_product(product: CreateProduct) -> CreateProduct:
    return product


def install_catalog(app: Any) -> None:
    app.mount_module(catalog, prefix="/api/products")
```

```python
# app/modules/ai_tools/module.py
from typing import Any

from fastmcp import FastMCP

from flaxon.integrations.fastmcp import mount_fastmcp

mcp = FastMCP("Store Tools")


@mcp.tool
async def find_product(name: str) -> dict[str, str | bool]:
    return {"name": name, "available": True}


def install_ai_tools(app: Any, auth_provider: Any) -> None:
    mount_fastmcp(
        app,
        mcp,
        path="/mcp",
        auth=auth_provider,
        require_auth=True,
        stateless_http=True,
    )
```

Mount both from one factory:

```python
# app/main.py
from flaxon import Flaxon

from app.auth import auth_provider
from app.modules.ai_tools.module import install_ai_tools
from app.modules.catalog.module import install_catalog


def create_app() -> Flaxon:
    app = Flaxon("store", debug=False)
    install_catalog(app)
    install_ai_tools(app, auth_provider)
    return app


app = create_app()
```

Install the optional dependencies explicitly:

```bash
python -m pip install "flaxon[pydantic,mcp]"
flaxon run app.main:app --reload
```

The resulting contracts are easy to find: normal JSON clients call
`POST /api/products/`, while MCP clients connect to `/mcp`. Pydantic validates
the JSON body; FastMCP handles MCP protocol messages; the feature service is
where shared business rules belong. Do not call `mcp.run()` when it is mounted
into Flaxon.

## Keep the application entry point small

The application entry point should compose feature routers and global
infrastructure; it should not contain product rules.

```python
# app/main.py
from flaxon import Flaxon
from flaxon.middleware import CORSMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware

from app.modules.accounts.routes import router as accounts_router
from app.modules.catalog.routes import router as catalog_router


def create_app() -> Flaxon:
    app = Flaxon("myapp", debug=False)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allowed_origins=["https://app.example.com"],
        allow_credentials=True,
    )
    app.include_router(accounts_router)
    app.include_router(catalog_router)
    return app


app = create_app()
```

Use explicit origins when credentials are enabled. Flaxon rejects the unsafe
combination of `allow_credentials=True` and `allowed_origins=["*"]`.

## Put HTTP code in routes and product rules in services

Routes convert HTTP input into a service call. Services should not depend on
`Request`, `Response`, or template objects, which keeps the same rule usable
from HTTP, WebSocket, task, and CLI entry points.

```python
# app/modules/catalog/routes.py
from flaxon import Router
from flaxon.validation import Schema, fields

from .service import CatalogService

router = Router(prefix="/api/v1/products")
service = CatalogService()


class CreateProduct(Schema):
    name = fields.StrField(required=True, min_length=1, max_length=200)
    price_cents = fields.IntField(required=True, minimum=0)


@router.post("")
async def create_product(data: CreateProduct) -> dict:
    product = await service.create(data.to_dict())
    return {"product": product}
```

```python
# app/modules/catalog/service.py
class CatalogService:
    async def create(self, values: dict) -> dict:
        # Call a repository or an external API here.
        return {"id": "new-product", **values}
```

## Draw clear ownership lines

| Concern | Put it in | Keep it out of |
|---|---|---|
| Path, method, status code, headers | route | service/repository |
| Input shape and validation | schema | template/business service |
| Product rules and workflows | service | route handler |
| Persistence queries | repository/infrastructure | route handler |
| Cross-cutting HTTP behavior | middleware | individual routes |
| HTML presentation | Jinax templates | service |

## Add capabilities deliberately

At this scale, use framework features where they match the boundary:

- **Middleware:** request IDs, security headers, CORS, body limits, trusted
  hosts, compression, logging, and timeouts.
- **Validation:** typed JSON payloads with `Schema` and the `*Field` classes.
- **Jinax:** server-rendered pages and reusable template layouts.
- **WebSockets:** real-time connections and in-process room broadcasts.
- **Tasks:** work that must not hold an HTTP request open.
- **Caching:** cache read-heavy, invalidation-safe data with `cached_async`.
- **Observability:** the built-in `/health`, `/health/live`, `/health/ready`,
  and `/metrics` endpoints, plus your own dependency checks.
- **OpenAPI and GraphQL:** enable only when the project actually exposes those
  interfaces.

## Plan for more than one worker

An in-memory object belongs to one Python process. That includes the default
session backend, task queue, cache, rate-limit state, and WebSocket room
manager. A multi-worker or multi-instance deployment must not rely on those
objects for shared state.

For a horizontally scaled application:

1. Keep route handlers stateless.
2. Store authoritative data in your database or object storage.
3. Use a shared service such as Redis when sessions, cached values, task
   coordination, or WebSocket fan-out must cross process boundaries.
4. Use the Redis-backed adapters only after installing and operating Redis;
   they are not part of the core install.
5. Run background workers separately from HTTP workers.

## Keep templates manageable

For 200 server-rendered pages, use a base template, feature-owned template
folders, and view models prepared by services/routes. Do not place database
queries, permission decisions, or network calls inside Jinax templates.

### Copy-paste feature module with Jinax

`Router` keeps a feature's endpoints together, while `Jinax` renders its
templates through the shared application engine:

```python
# app/main.py
from flaxon import Flaxon
from flaxon.jinax import Jinax
from app.modules.catalog.routes import router as catalog_router

app = Flaxon("catalog", debug=True)
app.use_templates(Jinax("app/templates", auto_reload=True))
app.include_router(catalog_router, prefix="/store")
```

```python
# app/modules/catalog/routes.py
from flaxon import Router

router = Router(prefix="/catalog")

@router.get("")
async def catalog(request):
    return await request.render("catalog/index.html", {
        "title": "Catalog",
        "products": [{"name": "Starter", "price": 19}],
    })
```

This serves `GET /store/catalog`. Create `app/templates/catalog/index.html`:

```html
<!doctype html>
<html><head><title>{{ title }}</title></head>
<body><h1>{{ title }}</h1>
{% for product in products %}<article>{{ product.name }}: ${{ product.price }}</article>{% endfor %}
</body></html>
```

Run `pip install "flaxon[templates]"` and
`flaxon run app.main:app --reload`.

## Test by feature and by boundary

- Unit-test services without an ASGI client.
- Use `TestClient` for routes, middleware, validation, and error responses.
- Use `AsyncWebSocketClient` for WebSocket protocol tests; use
  `AsyncTestClient` when the HTTP test itself runs inside an async test.
- Add integration tests for the real database/cache adapters you choose.
- Keep regression tests beside the feature that previously failed.

## Release checklist for a large application

- Production configuration has `DEBUG=False` and a non-default secret.
- CORS origins and trusted hosts are explicit.
- Database migrations, backups, and restore drills exist.
- In-memory defaults are not used as cross-worker shared state.
- Health checks cover critical dependencies.
- Metrics, structured logs, alerts, and request IDs are connected to your
  operations tooling.
- Load tests use the real ASGI server, deployment topology, and dependencies.
