
# Routing API

## Router

The main routing class used to register HTTP and WebSocket endpoints.

## Constructor

```python
Router(prefix: str = "")
````

### Parameters

| Parameter | Type | Description                               |
| --------- | ---- | ----------------------------------------- |
| prefix    | str  | Optional URL prefix applied to all routes |

---

# Methods

## add_route

```python
add_route(
    path: str,
    endpoint: Callable,
    *,
    methods: set[str] | list[str] | tuple[str, ...] = ("GET",),
    name: str | None = None
) -> Route
```

Add an HTTP route.

---

## add_websocket

```python
add_websocket(
    path: str,
    endpoint: Callable,
    *,
    name: str | None = None
) -> WebSocketRoute
```

Add a WebSocket route.

---

## route

```python
route(
    path: str,
    *,
    methods: set[str] | list[str] | tuple[str, ...] = ("GET",),
    name: str | None = None
) -> Callable
```

Decorator for registering an HTTP route.

---

## get

```python
get(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a GET route.

---

## post

```python
post(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a POST route.

---

## put

```python
put(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a PUT route.

---

## patch

```python
patch(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a PATCH route.

---

## delete

```python
delete(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a DELETE route.

---

## head

```python
head(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a HEAD route.

---

## options

```python
options(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register an OPTIONS route.

---

## websocket

```python
websocket(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Register a WebSocket route.

---

## include_router

```python
include_router(other: Router, prefix: str | None = None) -> None
```

Include routes from another router. When `prefix` is provided, the source
router prefix is removed and the new mount prefix is applied.

---

## match

```python
match(
    path: str,
    method: str
) -> RouteMatch
```

Match an HTTP request to a route.

---

## match_websocket

```python
match_websocket(
    path: str
) -> WebSocketMatch
```

Match a WebSocket connection to a route.

---

## url_for

```python
url_for(
    name: str,
    **params: Any
) -> str
```

Generate a URL for a named route.

---

# Properties

## routes

```python
@property
def routes(self) -> list[Route]
```

Get all registered HTTP routes.

---

## websocket_routes

```python
@property
def websocket_routes(self) -> list[WebSocketRoute]
```

Get all registered WebSocket routes.

---

## route_count

```python
@property
def route_count(self) -> int
```

Get the number of HTTP routes.

---

## websocket_count

```python
@property
def websocket_count(self) -> int
```

Get the number of WebSocket routes.

---

## total_count

```python
@property
def total_count(self) -> int
```

Get the total number of routes.

---

# Route

HTTP route definition.

## Attributes

| Attribute  | Type       | Description           |
| ---------- | ---------- | --------------------- |
| path       | str        | URL path pattern      |
| endpoint   | Callable   | Endpoint function     |
| methods    | set[str]   | Allowed HTTP methods  |
| name       | str | None | Route name            |
| regex      | re.Pattern | Compiled route regex  |
| parameters | list[str]  | Route parameter names |

---

## Methods

### match_path

```python
match_path(
    path: str
) -> dict[str, Any] | None
```

Match a path against this route.

---

# WebSocketRoute

WebSocket route definition.

## Attributes

| Attribute  | Type       | Description                |
| ---------- | ---------- | -------------------------- |
| path       | str        | WebSocket URL path pattern |
| endpoint   | Callable   | Endpoint function          |
| name       | str | None | Route name                 |
| regex      | re.Pattern | Compiled route regex       |
| parameters | list[str]  | Route parameter names      |

---

## Methods

### match_path

```python
match_path(
    path: str
) -> dict[str, Any] | None
```

Match a path against this WebSocket route.

---

# RouteMatch

Result of an HTTP route match.

## Attributes

| Attribute | Type           | Description               |
| --------- | -------------- | ------------------------- |
| route     | Route          | Matched route             |
| params    | dict[str, Any] | Extracted path parameters |

---

# WebSocketMatch

Result of a WebSocket route match.

## Attributes

| Attribute | Type           | Description               |
| --------- | -------------- | ------------------------- |
| route     | WebSocketRoute | Matched WebSocket route   |
| params    | dict[str, Any] | Extracted path parameters |


## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
