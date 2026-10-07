# Middleware

## Overview

Middleware allows you to intercept requests before they reach your route handlers and modify responses before they are returned to the client.

Middleware is commonly used for:

- Authentication
- Logging
- CORS
- Compression
- Rate limiting
- Security headers
- Request IDs
- Request validation
- Error handling
- Timeouts

Flaxon middleware follows the ASGI specification and works with both HTTP and WebSocket applications.

---

# Adding Middleware

```python
from flaxon import Flaxon
from flaxon.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    CORSMiddleware,
)

app = Flaxon("my-app")

app.add_middleware(
    RequestIDMiddleware,
    header_name="X-Request-ID"
)

app.add_middleware(
    SecurityHeadersMiddleware
)

app.add_middleware(
    CORSMiddleware,
    allowed_origins=["https://example.com"],
    allow_credentials=True,
)
```

---

# Built-in Middleware

Flaxon includes middleware suitable for production after application-specific
configuration and testing.

| Middleware | Purpose |
|------------|---------|
| RequestIDMiddleware | Adds request IDs |
| SecurityHeadersMiddleware | Adds common security headers |
| CORSMiddleware | Handles Cross-Origin Resource Sharing |
| CompressionMiddleware | Compresses responses |
| BodyLimitMiddleware | Limits request body size |
| TimeoutMiddleware | Cancels slow requests |
| LoggingMiddleware | Logs requests and responses |
| RecoveryMiddleware | Handles uncaught exceptions |
| TrustedHostsMiddleware | Validates the Host header |
| RateLimitMiddleware | Limits request frequency |

---

# RequestIDMiddleware

Assigns a unique identifier to every request.

```python
from flaxon.middleware import RequestIDMiddleware

app.add_middleware(
    RequestIDMiddleware,
    header_name="X-Request-ID"
)
```

Useful for:

- Debugging
- Log correlation
- Distributed tracing

---

# SecurityHeadersMiddleware

Automatically adds common security headers.

```python
from flaxon.middleware import SecurityHeadersMiddleware

app.add_middleware(

    SecurityHeadersMiddleware,

    headers={
        "strict-transport-security": "max-age=31536000; includeSubDomains",
        "content-security-policy": "default-src 'self'",
    }
)
```

Default headers include:

- X-Content-Type-Options
- X-Frame-Options

---

# CORSMiddleware

Handles browser Cross-Origin Resource Sharing.

```python
from flaxon.middleware import CORSMiddleware

app.add_middleware(

    CORSMiddleware,

    allowed_origins=[
        "https://example.com"
    ],

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE"
    ],

    allow_credentials=True
)
```

---

# CompressionMiddleware

Compresses large responses.

```python
from flaxon.middleware import CompressionMiddleware

app.add_middleware(

    CompressionMiddleware,

    minimum_size=1024,

    level=6
)
```

Supported compression:

- Gzip
- Deflate
- Brotli (optional)

---

# BodyLimitMiddleware

Prevents oversized request bodies.

```python
from flaxon.middleware import BodyLimitMiddleware

app.add_middleware(

    BodyLimitMiddleware,

    max_size=10 * 1024 * 1024
)
```

---

# TimeoutMiddleware

Stops requests that exceed a time limit.

```python
from flaxon.middleware import TimeoutMiddleware

app.add_middleware(

    TimeoutMiddleware,

    timeout=30
)
```

---

# TrustedHostsMiddleware

Restricts requests to approved host names.

```python
from flaxon.middleware import TrustedHostsMiddleware

app.add_middleware(

    TrustedHostsMiddleware,

    allowed_hosts=[

        "example.com",

        "api.example.com"

    ]

)
```

---

# LoggingMiddleware

Logs incoming requests and outgoing responses.

```python
from flaxon.middleware import LoggingMiddleware

app.add_middleware(

    LoggingMiddleware,

    log_headers=True,

    log_body=False
)
```

Useful for:

- Development
- Monitoring
- Auditing

---

# RecoveryMiddleware

Catches uncaught exceptions and returns safe error responses.

```python
from flaxon.middleware import RecoveryMiddleware

app.add_middleware(

    RecoveryMiddleware,

    debug=False
)
```

In debug mode, detailed information appears in the Debug Dashboard.

---

# RateLimitMiddleware

Protects endpoints from abuse.

```python
from flaxon.security import RateLimitMiddleware

app.add_middleware(

    RateLimitMiddleware,

    requests=60,

    window_seconds=60
)
```

---

# Middleware Order

Middleware executes in the order it is registered.

```python
app.add_middleware(RequestIDMiddleware)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(CORSMiddleware)

app.add_middleware(CustomMiddleware)
```

Execution flow:

```text
Incoming Request

        │

        ▼

RequestIDMiddleware

        ▼

SecurityHeadersMiddleware

        ▼

CORSMiddleware

        ▼

CustomMiddleware

        ▼

Route Handler

        ▲

CustomMiddleware

        ▲

CORSMiddleware

        ▲

SecurityHeadersMiddleware

        ▲

RequestIDMiddleware

        ▲

Outgoing Response
```

The first middleware added is the outermost middleware.

---

# Creating Custom Middleware

Custom middleware extends the base `Middleware` class.

```python
from flaxon.middleware import Middleware


class CustomMiddleware(Middleware):

    def __init__(

        self,

        app,

        header_name="X-Custom"

    ):

        super().__init__(app)

        self.header_name = header_name


    async def __call__(

        self,

        scope,

        receive,

        send

    ):

        if scope["type"] != "http":

            return await self.app(

                scope,

                receive,

                send

            )


        scope["custom"] = True


        async def send_wrapper(message):

            if message["type"] == "http.response.start":

                headers = list(

                    message.get(

                        "headers",

                        []

                    )

                )

                headers.append(

                    (

                        self.header_name.encode(),

                        b"enabled"

                    )

                )

                message["headers"] = headers

            await send(message)


        await self.app(

            scope,

            receive,

            send_wrapper

        )
```

---

# Conditional Middleware

Middleware can inspect requests before deciding what to do.

```python
from flaxon.middleware import Middleware


class APIMiddleware(Middleware):

    async def __call__(

        self,

        scope,

        receive,

        send

    ):

        path = scope.get("path", "")

        if path.startswith("/api"):

            print("API request")

        await self.app(

            scope,

            receive,

            send
        )
```

---

# WebSocket Middleware

Middleware also supports WebSocket connections.

```python
class WebSocketLogger(Middleware):

    async def __call__(

        self,

        scope,

        receive,

        send

    ):

        if scope["type"] == "websocket":

            print(

                "WebSocket connected:",

                scope["path"]

            )

        await self.app(

            scope,

            receive,

            send

        )
```

---

# Complete Example

```python
from flaxon import Flaxon

from flaxon.middleware import (

    RequestIDMiddleware,

    SecurityHeadersMiddleware,

    CORSMiddleware,

    CompressionMiddleware,

    BodyLimitMiddleware,

    TimeoutMiddleware,

    LoggingMiddleware,

    RecoveryMiddleware,

)

from flaxon.security import RateLimitMiddleware


app = Flaxon("middleware-demo")


app.add_middleware(RequestIDMiddleware)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(RecoveryMiddleware)

app.add_middleware(LoggingMiddleware)

app.add_middleware(

    CORSMiddleware,

    allowed_origins=[

        "https://example.com"

    ]

)

app.add_middleware(

    CompressionMiddleware

)

app.add_middleware(

    RateLimitMiddleware,

    requests=60,

    window_seconds=60

)

app.add_middleware(

    BodyLimitMiddleware,

    max_size=10 * 1024 * 1024

)

app.add_middleware(

    TimeoutMiddleware,

    timeout=30

)


@app.get("/")
async def home():

    return {

        "message": "Hello from Flaxon"

    }
```

---

# Debugging Middleware

When debug mode is enabled, middleware errors are recorded in the Debug Dashboard.

Open:

```text
http://localhost:8000/__debug__
```

The dashboard displays:

- Middleware execution order
- Exceptions
- Stack traces
- Request headers
- Response headers
- Request IDs
- Processing time
- Registered middleware
- Performance information

Sensitive information is automatically redacted.

---

# Best Practices

- Keep middleware lightweight.
- Avoid database queries inside middleware unless necessary.
- Register middleware in a logical order.
- Prefer asynchronous operations.
- Avoid blocking the event loop.
- Keep middleware focused on a single responsibility.
- Use request IDs for debugging.
- Enable compression in production.
- Enable logging during development.
- Configure security middleware before deployment.

---

# API Reference

See the Middleware API Reference for complete documentation of:

- Middleware
- RequestIDMiddleware
- CORSMiddleware
- CompressionMiddleware
- SecurityHeadersMiddleware
- RecoveryMiddleware
- TimeoutMiddleware
- LoggingMiddleware
- TrustedHostsMiddleware
- BodyLimitMiddleware
- RateLimitMiddleware

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
