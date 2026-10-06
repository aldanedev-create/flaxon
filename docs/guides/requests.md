# Requests

## Overview

The `Request` object provides access to everything sent by the client, including:

- HTTP method
- URL
- Headers
- Query parameters
- Path parameters
- Cookies
- Body content
- Form data
- Uploaded files
- Client information
- Request state

A `Request` instance is automatically injected into route handlers when requested.

---

# Accessing the Request

```python
from flaxon import Flaxon, Request

app = Flaxon("my-app")

@app.get("/")
async def home(request: Request):
    return {
        "method": request.method,
        "path": request.path,
    }
```

---

# Request Properties

```python
@app.get("/info")
async def info(request: Request):
    return {
        "method": request.method,
        "path": request.path,
        "url": request.url,
        "scheme": request.scheme,
        "host": request.host,
        "client": request.client,
        "http_version": request.http_version,
    }
```

Common properties:

| Property | Description |
|----------|-------------|
| `method` | HTTP method |
| `path` | Request path |
| `url` | Full URL |
| `scheme` | http or https |
| `host` | Host name |
| `client` | Client IP address |
| `headers` | HTTP headers |
| `cookies` | Cookies |
| `query` | Query parameters |
| `state` | Request-local storage |

---

# HTTP Headers

Read individual headers:

```python
@app.get("/headers")
async def headers(request: Request):

    return {
        "user_agent": request.headers.get("user-agent"),
        "accept": request.headers.get("accept"),
        "content_type": request.headers.get("content-type"),
    }
```

Return every header:

```python
@app.get("/all-headers")
async def headers(request: Request):

    return dict(request.headers)
```

Check for a header:

```python
if "authorization" in request.headers:
    ...
```

---

# Query Parameters

URL:

```
/search?q=python&page=2&category=books
```

Access them:

```python
@app.get("/search")
async def search(request: Request):

    query = request.query.get("q")

    page = request.query.get_int(
        "page",
        1,
    )

    category = request.query.get(
        "category"
    )

    return {
        "query": query,
        "page": page,
        "category": category,
    }
```

---

# Typed Query Helpers

```python
page = request.query.get_int("page", 1)

price = request.query.get_float("price")

active = request.query.get_bool("active")

tags = request.query.get_list("tag")
```

Available helpers:

- `get()`
- `get_int()`
- `get_float()`
- `get_bool()`
- `get_list()`

---

# Path Parameters

```python
@app.get("/users/<int:user_id>")
async def user(user_id: int):

    return {
        "user_id": user_id
    }
```

Multiple parameters:

```python
@app.get("/users/<int:user_id>/posts/<int:post_id>")
async def post(
    user_id: int,
    post_id: int,
):

    return {
        "user": user_id,
        "post": post_id,
    }
```

---

# Cookies

Read cookies:

```python
@app.get("/profile")
async def profile(request: Request):

    session = request.cookies.get(
        "session_id"
    )

    theme = request.cookies.get(
        "theme",
        "light",
    )

    return {
        "session": session,
        "theme": theme,
    }
```

---

# Reading JSON

```python
@app.post("/users")
async def create_user(request: Request):

    data = await request.json()

    return data
```

---

# Reading Plain Text

```python
@app.post("/text")
async def text(request: Request):

    body = await request.text()

    return {
        "length": len(body)
    }
```

---

# Reading Raw Bytes

```python
@app.post("/binary")
async def binary(request: Request):

    data = await request.body()

    return {
        "bytes": len(data)
    }
```

---

# Form Data

```python
@app.post("/contact")
async def contact(request: Request):

    form = await request.form()

    return {
        "name": form.get("name"),
        "email": form.get("email"),
    }
```

---

# File Uploads

```python
@app.post("/upload")
async def upload(request: Request):

    form = await request.form()

    file = form["file"]

    return {
        "filename": file.filename,
        "content_type": file.content_type,
    }
```

---

# Automatic Validation

Schemas automatically validate incoming data.

```python
from flaxon.validation import Schema, fields

class CreateUser(Schema):

    name = fields.StrField(
        required=True,
        min_length=2,
    )

    email = fields.EmailField(
        required=True,
    )

    age = fields.IntField(
        minimum=13,
    )
```

Use the schema:

```python
@app.post("/users")
async def create_user(data: CreateUser):

    return data.to_dict()
```

---

# Combining Request and Validation

```python
@app.post("/users")
async def create_user(
    request: Request,
    data: CreateUser,
):

    return {
        "ip": request.client,
        "user": data.to_dict(),
    }
```

---

# Request State

Store data during request processing.

```python
@app.get("/")
async def home(request: Request):

    request.state.user_id = 15

    return {
        "user": request.state.user_id
    }
```

Middleware:

```python
request.state.start_time = time.time()
```

Route:

```python
elapsed = time.time() - request.state.start_time
```

---

# Client Information

```python
@app.get("/client")
async def client(request: Request):

    return {
        "ip": request.client,
        "user_agent": request.headers.get("user-agent"),
    }
```

---

# Authentication Information

When authentication middleware is enabled:

```python
@app.get("/profile")
async def profile(request: Request):

    user = request.user

    return user.to_dict()
```

---

# Request Context

Access the current request anywhere in your application.

```python
from flaxon.application.context import get_current_request

request = get_current_request()
```

Example:

```python
def current_ip():

    request = get_current_request()

    return request.client
```

---

# Reading Large Bodies

For very large uploads use streaming.

```python
@app.post("/upload")
async def upload(request: Request):

    async for chunk in request.stream():

        process(chunk)

    return {
        "uploaded": True
    }
```

Streaming avoids loading the entire request into memory.

---

# Complete Example

```python
from flaxon import Flaxon, Request
from flaxon.validation import Schema, fields

app = Flaxon("request-demo")

class CreateUser(Schema):

    username = fields.StrField(required=True)

    email = fields.EmailField(required=True)

@app.get("/users/<int:user_id>")
async def get_user(
    user_id: int,
    request: Request,
):

    return {
        "user_id": user_id,
        "include_posts": request.query.get_bool(
            "posts",
            False,
        ),
        "client": request.client,
    }

@app.post("/users")
async def create_user(
    request: Request,
    data: CreateUser,
):

    return {
        "success": True,
        "user": data.to_dict(),
        "session": request.cookies.get("session_id"),
    }
```

---

# Best Practices

- Use schema validation whenever possible.
- Use typed query helpers instead of manual conversion.
- Keep request handlers lightweight.
- Avoid reading the body multiple times.
- Use streaming for large uploads.
- Store request-specific data in `request.state`.
- Never trust client input without validation.
- Use HTTPS in production.
- Protect sensitive endpoints with authentication and authorization.
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
