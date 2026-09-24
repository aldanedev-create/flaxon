# Routing

## Overview

Flaxon provides a fast, flexible, and familiar routing system for building web applications and APIs. Routes are registered using decorators on your application or on reusable routers.

**Features**

- Decorator-based routing
- Async-first request handling
- Angle-bracket route parameters
- Nested routers
- Route groups
- Named routes
- URL generation
- Sub-application mounting
- Route inspection via CLI

---

# Basic Routes

```python
from flaxon import Flaxon

app = Flaxon("my-app")


@app.get("/")
async def home():
    return {"message": "Hello, World!"}


@app.post("/users")
async def create_user():
    return {"created": True}


@app.put("/users/<int:user_id>")
async def update_user(user_id: int):
    return {
        "updated": True,
        "id": user_id,
    }


@app.delete("/users/<int:user_id>")
async def delete_user(user_id: int):
    return {
        "deleted": True,
        "id": user_id,
    }
```

---

# Supported HTTP methods

Flaxon provides convenience decorators for `GET`, `POST`, `PUT`, `PATCH`, and
`DELETE`. Register another method explicitly with `app.route()`.

```python
@app.get("/")
async def get_route():
    ...


@app.post("/")
async def post_route():
    ...


@app.put("/")
async def put_route():
    ...


@app.patch("/")
async def patch_route():
    ...


@app.delete("/")
async def delete_route():
    ...


@app.route("/", methods={"HEAD", "OPTIONS"})
async def metadata_route():
    ...
```

---

# Route Parameters

## Flask-Style Parameters

```python
@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {"id": user_id}


@app.get("/posts/<slug:slug>")
async def get_post(slug: str):
    return {"slug": slug}


@app.get("/files/<path:file_path>")
async def get_file(file_path: str):
    return {"path": file_path}
```

---

# Supported Parameter Converters

| Converter | Description | Example |
|-----------|-------------|---------|
| `str` | Default string | `<name>` |
| `int` | Integer | `<int:user_id>` |
| `float` | Floating point | `<float:price>` |
| `path` | Path including `/` | `<path:file>` |
| `uuid` | UUID value | `<uuid:token>` |
| `slug` | URL-safe slug string | `<slug:article>` |

---

# Typed Query Parameters

```python
from flaxon import Query


@app.get("/search")
async def search(
    query: str = Query("", alias="q", max_length=120),
    page: int = Query(1, ge=1),
):
    return {"query": query, "page": page}
```

`Query()` without a default is required. Values are coerced and invalid
values return a `422` validation response. Query declarations are included in
automatic OpenAPI documentation; see the [OpenAPI guide](openapi.md).

---

# Route Prefixes

```python
from flaxon import Router

api = Router(prefix="/api/v1")


@api.get("/users")
async def users():
    return []


@api.get("/posts")
async def posts():
    return []


app.include_router(api)
```

## Specificity and safe mounts

Literal routes take precedence over parameter routes, regardless of registration
order. Registration order is retained only when matching routes have equal
specificity.

```python
from flaxon import Flaxon, Router

app = Flaxon("routing-example")

@app.get("/admin/<model_name>")
async def model(model_name: str):
    return {"model": model_name}

@app.get("/admin/cms")
async def cms():
    return {"panel": "cms"}  # wins over /admin/<model_name>

api = Router(prefix="/api")

@api.get("/items/<int:item_id>")
async def item(item_id: int):
    return {"id": item_id}

app.include_router(api, prefix="/v1")  # GET /v1/items/7
```

`include_router(router, prefix=...)` strips the source router prefix before
applying the mount prefix, so one router can be mounted at multiple locations.
Overlapping patterns with the same HTTP method produce a registration warning.

Endpoints:

```
GET /api/v1/users
GET /api/v1/posts
```

---

# Routers

```python
from flaxon import Router

api = Router(prefix="/api")


@api.get("/users")
async def users():
    return []


@api.post("/users")
async def create_user():
    return {"created": True}


app.include_router(api)
```

---

# Route Groups

```python
from flaxon.routing import RouteGroup

admin = RouteGroup(prefix="/admin")


@admin.get("/dashboard")
async def dashboard():
    return {"admin": True}


@admin.get("/users")
async def users():
    return []


app.include_router(admin.as_router())
```

---

# Nested Routers

```python
from flaxon import Router

api = Router(prefix="/api")

v1 = Router(prefix="/v1")
v2 = Router(prefix="/v2")


@v1.get("/users")
async def users_v1():
    return {
        "version": "v1",
    }


@v2.get("/users")
async def users_v2():
    return {
        "version": "v2",
    }


api.include_router(v1)
api.include_router(v2)

app.include_router(api)
```

Available routes

```
/api/v1/users
/api/v2/users
```

---

# Named Routes

```python
@app.get(
    "/users/<int:user_id>",
    name="users.detail",
)
async def user_detail(user_id: int):
    return {
        "id": user_id,
    }
```

Generate URLs:

```python
url = app.url_for(
    "users.detail",
    user_id=42,
)

print(url)

# /users/42
```

---

# Route Matching

Literal routes take precedence over dynamic routes regardless of registration
order. Registration order is used only when matching routes have equal
specificity.

```python
@app.get("/users/me")
async def current_user():
    return {
        "username": "admin",
    }


@app.get("/users/<int:user_id>")
async def user(user_id: int):
    return {
        "id": user_id,
    }
```

---

# Multiple Decorators

A single handler can respond to multiple routes.

```python
@app.get("/")
@app.get("/home")
async def home():
    return {
        "message": "Welcome",
    }
```

---

# Route Metadata

```python
@app.get(
    "/products",
    name="products.list",
    tags=["Products"],
    summary="List products",
)
async def products():
    return []
```

---

# Error Handling

```python
from flaxon import HTTPException


@app.get("/users/<int:user_id>")
async def get_user(user_id: int):

    if user_id == 0:
        raise HTTPException(
            400,
            "Invalid user ID",
            code="FX-INVALID-ID",
        )

    if user_id == 404:
        raise HTTPException(
            404,
            "User not found",
            code="FX-USER-404",
        )

    return {
        "id": user_id,
        "name": f"User {user_id}",
    }
```

---

# Mounting Applications

```python
from flaxon import Flaxon
from flaxon.routing import Mount

admin = Flaxon("admin")


@admin.get("/")
async def dashboard():
    return {
        "admin": True,
    }


app.include_router(
    Mount("/admin", admin)
)
```

Routes

```
/admin/
```

---

# API Versioning

```python
from flaxon import Router

v1 = Router(prefix="/api/v1")
v2 = Router(prefix="/api/v2")


@v1.get("/users")
async def users_v1():
    return {
        "version": 1,
    }


@v2.get("/users")
async def users_v2():
    return {
        "version": 2,
    }


app.include_router(v1)
app.include_router(v2)
```

---

# Route Inspection

List every registered route.

```bash
flaxon routes app:app
```

Example output

```text
Method   Path                      Name
GET      /                         home
POST     /users                    create_user
PUT      /users/<int:user_id>      update_user
DELETE   /users/<int:user_id>      delete_user
GET      /api/v1/users             users
GET      /about                    about
```

---

# Complete Example

```python
from flaxon import Flaxon, Router
from flaxon.routing import RouteGroup

app = Flaxon("routing-demo")


@app.get("/")
async def home():
    return {
        "message": "Welcome to Flaxon",
    }


@app.get("/users/<int:user_id>")
async def user(user_id: int):
    return {
        "id": user_id,
        "name": f"User {user_id}",
    }


api = Router(prefix="/api/v1")


@api.get("/products")
async def products():
    return [
        {
            "id": 1,
            "name": "Laptop",
        },
        {
            "id": 2,
            "name": "Keyboard",
        },
    ]


app.include_router(api)


admin = RouteGroup(prefix="/admin")


@admin.get("/dashboard")
async def dashboard():
    return {
        "users": 152,
        "orders": 89,
    }


app.include_router(admin.as_router())


@app.get("/about", name="about")
async def about():
    return {
        "framework": "Flaxon",
        "version": "1.0.0",
    }


about_url = app.url_for("about")
print(about_url)
```

---

# Best Practices

- Group related routes using `Router`.
- Use API versioning for public APIs.
- Register specific routes before dynamic routes.
- Use named routes for URL generation.
- Keep route handlers focused on request handling.
- Move business logic into services.
- Validate request data using schemas.
- Return consistent JSON responses.
- Organize large applications into multiple routers.
- Mount sub-applications when building modular systems.
