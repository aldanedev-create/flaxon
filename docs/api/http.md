# HTTP API

---

# Request

HTTP request object.

---

## Constructor

```python
Request(
    scope: dict[str, Any],
    receive: Any,
    app: Any
)
```

---

## Properties

| Property | Type | Description |
|---|---|---|
| `method` | `str` | HTTP method |
| `path` | `str` | Request path |
| `root_path` | `str` | Root path |
| `scheme` | `str` | URL scheme |
| `headers` | `Headers` | Request headers |
| `path_params` | `dict[str, Any]` | Path parameters |
| `state` | `SimpleNamespace` | Request state |
| `user` | `Any` | Authenticated user |
| `query` | `QueryParams` | Query parameters |
| `cookies` | `Cookies` | Cookies |
| `client` | `tuple[str, int] \| None` | Client address |
| `host` | `str` | Host header |
| `url` | `str` | Full URL |

---

## Methods

### body

```python
async def body() -> bytes
```

Get the request body as bytes.

---

### json

```python
async def json() -> Any
```

Get the request body as JSON.

---

### text

```python
async def text() -> str
```

Get the request body as text.

---

### form

```python
async def form() -> dict[str, Any]
```

Get the request body as form data.

---

### render

```python
async def render(
    template_name: str,
    context: dict[str, Any] | None = None
) -> Any
```

Render a template using Jinax.

---

# Response

HTTP response object.

---

## Constructor

```python
Response(
    content: bytes | str = b"",
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str | None = None
)
```

---

## Class Methods

### from_value

```python
@classmethod
def from_value(
    cls,
    value: Any
) -> Response
```

Convert a value to a response.

---

# Response Types

---

## JSONResponse

JSON response.

### Constructor

```python
JSONResponse(
    content: Any,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

---

## HTMLResponse

HTML response.

### Constructor

```python
HTMLResponse(
    content: str,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

---

## TextResponse

Plain text response.

### Constructor

```python
TextResponse(
    content: str,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

---

## RedirectResponse

Redirect response.

### Constructor

```python
RedirectResponse(
    url: str,
    status_code: int = 307,
    headers: dict[str, str] | None = None
)
```

---

## StreamingResponse

Streaming response.

### Constructor

```python
StreamingResponse(
    content: AsyncIterator[bytes] | Iterable[bytes],
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str = "application/octet-stream"
)
```

---

# Headers

HTTP headers dictionary.

---

## Constructor

```python
Headers(
    raw: list[tuple[bytes, bytes]] | None = None
)
```

---

## Methods

### get

```python
get(
    key: str,
    default: Any = None
) -> Any
```

Get a header value with a default.

---

### get_raw

```python
get_raw(
    key: str
) -> bytes | None
```

Get a header value as bytes.

---

### to_list

```python
to_list() -> list[tuple[bytes, bytes]]
```

Convert headers to raw ASGI format.

---

### to_dict

```python
to_dict() -> dict[str, str]
```

Convert headers to a regular dictionary.

---

# Cookies

HTTP cookies dictionary.

---

## Methods

### get

```python
get(
    key: str,
    default: Any = None
) -> Any
```

Get a cookie value with a default.

---

### set

```python
set(
    key: str,
    value: str,
    *,
    max_age: int | None = None,
    expires: datetime | None = None,
    path: str | None = None,
    domain: str | None = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: str | None = None
) -> None
```

Set a cookie with options.

---

### delete

```python
delete(
    key: str
) -> None
```

Delete a cookie.

---

### set_delete

```python
set_delete(
    key: str,
    path: str | None = None
) -> None
```

Set a cookie to be deleted.

---

### to_dict

```python
to_dict() -> dict[str, str]
```

Convert cookies to a dictionary.

---

### to_headers

```python
to_headers() -> list[str]
```

Convert cookies to `Set-Cookie` headers.

---

# QueryParams

Query parameters dictionary.

---

## Methods

### get

```python
get(
    key: str,
    default: Any = None
) -> Any
```

Get a parameter value.

---

### get_list

```python
get_list(
    key: str
) -> list[str]
```

Get a parameter as a list.

---

### get_int

```python
get_int(
    key: str,
    default: int | None = None
) -> int | None
```

Get a parameter as an integer.

---

### get_float

```python
get_float(
    key: str,
    default: float | None = None
) -> float | None
```

Get a parameter as a float.

---

### get_bool

```python
get_bool(
    key: str,
    default: bool | None = None
) -> bool | None
```

Get a parameter as a boolean.

---

### get_all

```python
get_all() -> dict[str, list[str]]
```

Get all parameters as a dictionary of lists.

---

### to_dict

```python
to_dict() -> dict[str, str | list[str]]
```

Convert to a dictionary.

---

### to_query_string

```python
to_query_string() -> str
```

Convert to a query string.
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
