# Modules Example: Catalog and Orders

This is a small production-style application composed from independent
`FlaxonModule` features. It demonstrates the boundary that scales to a larger
application without putting every route in `app.py`:

```text
docs/examples/Modules/
|-- app.py
|-- modules/
|   |-- catalog.py
|   |-- orders.py
|   `-- store.py
`-- templates/store.html
```

## Run it

Install the framework and Jinax, then run from the repository root:

```bash
python -m pip install -e ".[templates]"
flaxon run docs.examples.Modules.app:app --reload
```

Open <http://127.0.0.1:8000/store/> to view the catalog. The API endpoints
are:

| Method | URL | Purpose |
|---|---|---|
| `GET` | `/store/` | Jinax storefront owned by the catalog module |
| `GET` | `/store/api/products` | Catalog JSON |
| `GET` | `/store/api/products/1` | One product |
| `GET` | `/api/orders/` | Orders JSON |
| `POST` | `/api/orders/` | Validate and create an order |

Create an order:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":2,"customer_email":"ada@example.com"}'
```

## What the example demonstrates

- `catalog.py` owns storefront and product routes.
- `orders.py` owns order validation and order routes.
- `store.py` is a shared service boundary. It is in-memory only so the demo
  needs no database; replace it with a repository for production persistence.
- `app.py` registers the service and decides the public URL prefixes with
  `app.mount_module(...)`.
- `requires("store")` makes a missing service fail during startup instead of
  failing on the first request.
- The same module pattern works for authentication, billing, admin pages,
  WebSockets, background tasks, and optional Pydantic or FastMCP integrations.

The module does not start its own server. The application factory owns
composition and the normal Flaxon CLI owns the server lifecycle.
