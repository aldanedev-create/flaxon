# Responses

## Overview

Flaxon automatically converts Python return values into HTTP responses. In most cases you can simply return a dictionary, list, string, or bytes, and Flaxon will generate the appropriate response.

Supported response types include:

- JSON
- HTML
- Plain text
- Files
- Redirects
- Streams
- Custom response classes

---

# Automatic Response Conversion

Flaxon automatically converts common Python types into HTTP responses.

```python
@app.get("/")
async def home():

    # Dictionary → JSON
    return {
        "message": "Hello, Flaxon!"
    }
```

```python
@app.get("/users")
async def users():

    # List → JSON
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
```

```python
@app.get("/text")
async def text():

    # String → text/plain
    return "Hello World"
```

```python
@app.get("/bytes")
async def bytes_response():

    # Bytes → application/octet-stream
    return b"Binary Data"
```

```python
@app.get("/empty")
async def empty():

    # None → HTTP 204
    return None
```

---

# Response Classes

Flaxon provides specialized response classes when additional control is needed.

Available responses:

- Response
- JSONResponse
- HTMLResponse
- TextResponse
- FileResponse
- RedirectResponse
- StreamingResponse

---

# JSONResponse

```python
from flaxon import JSONResponse

@app.get("/json")
async def json():

    return JSONResponse(
        {
            "status": "success",
            "items": [1, 2, 3],
        },
        status_code=200,
    )
```

---

# HTMLResponse

```python
from flaxon import HTMLResponse

@app.get("/page")
async def page():

    return HTMLResponse(
        """
        <h1>Welcome</h1>
        <p>Hello from Flaxon!</p>
        """
    )
```

---

# TextResponse

```python
from flaxon import TextResponse

@app.get("/robots.txt")
async def robots():

    return TextResponse(
        "User-agent: *\nDisallow:"
    )
```

---

# FileResponse

Serve existing files.

```python
from flaxon import FileResponse

@app.get("/download")
async def download():

    return FileResponse(
        "downloads/manual.pdf"
    )
```

Specify a download filename.

```python
return FileResponse(
    "downloads/report.pdf",
    filename="report.pdf",
)
```

---

# RedirectResponse

```python
from flaxon import RedirectResponse

@app.get("/old")
async def old():

    return RedirectResponse(
        "/new"
    )
```

Permanent redirect:

```python
return RedirectResponse(
    "/new",
    status_code=301,
)
```

---

# Redirect Helpers

```python
from flaxon.http.redirects import Redirect

@app.get("/login")
async def login():

    return Redirect.temporary(
        "/dashboard"
    )
```

Permanent redirect:

```python
return Redirect.permanent("/")
```

---

# StreamingResponse

Useful for large downloads and generated content.

```python
from flaxon import StreamingResponse

async def generator():

    for i in range(5):
        yield f"Line {i}\n".encode()

@app.get("/stream")
async def stream():

    return StreamingResponse(
        generator(),
        media_type="text/plain",
    )
```

---

# Returning Status Codes

Return a tuple.

```python
from flaxon.http.status import CREATED

@app.post("/users")
async def create():

    return {
        "created": True
    }, CREATED
```

Or use a response object.

```python
return JSONResponse(
    {"created": True},
    status_code=201,
)
```

---

# HTTP Status Constants

```python
from flaxon.http.status import (
    OK,
    CREATED,
    ACCEPTED,
    NO_CONTENT,
    BAD_REQUEST,
    UNAUTHORIZED,
    FORBIDDEN,
    NOT_FOUND,
    INTERNAL_SERVER_ERROR,
)
```

Example:

```python
return {
    "error": "Not Found"
}, NOT_FOUND
```

---

# Custom Headers

```python
return JSONResponse(
    {
        "status": "ok"
    },
    headers={
        "X-Request-ID": "12345",
        "X-Version": "1.0",
    },
)
```

---

# Cookies

```python
@app.post("/login")
async def login():

    response = JSONResponse(
        {"success": True}
    )

    response.set_cookie(
        "session",
        "abc123",
        httponly=True,
    )

    return response
```

Delete a cookie.

```python
response.delete_cookie("session")
```

---

# Content Types

Specify the media type.

```python
return Response(
    "<xml></xml>",
    media_type="application/xml",
)
```

---

# File Downloads

```python
from flaxon import FileResponse

@app.get("/report")
async def report():

    return FileResponse(
        "reports/annual.pdf",
        filename="annual-report.pdf",
    )
```

---

# Streaming Large Files

```python
import aiofiles

async def file_stream(path):

    async with aiofiles.open(path, "rb") as file:

        while chunk := await file.read(8192):
            yield chunk

@app.get("/video")
async def video():

    return StreamingResponse(
        file_stream("movie.mp4"),
        media_type="video/mp4",
    )
```

Streaming avoids loading the entire file into memory.

---

# Custom Response Classes

Create reusable response types.

```python
from flaxon import Response

class CSVResponse(Response):

    media_type = "text/csv"

    def __init__(
        self,
        rows,
        **kwargs,
    ):

        content = "\n".join(
            ",".join(row)
            for row in rows
        )

        super().__init__(
            content,
            **kwargs,
        )
```

Usage:

```python
@app.get("/export")
async def export():

    return CSVResponse([
        ["Name", "Email"],
        ["Alice", "alice@example.com"],
    ])
```

---

# Response Compression

When `CompressionMiddleware` is enabled, responses are automatically compressed.

```python
app.add_middleware(
    CompressionMiddleware
)
```

Supported algorithms:

- gzip
- deflate
- brotli

---

# Response Caching

Example:

```python
return JSONResponse(
    data,
    headers={
        "Cache-Control": "public, max-age=300"
    },
)
```

---

# Complete Example

```python
from flaxon import (
    Flaxon,
    JSONResponse,
    HTMLResponse,
    RedirectResponse,
    StreamingResponse,
    FileResponse,
)

app = Flaxon("responses-demo")

@app.get("/")
async def home():

    return {
        "message": "Welcome to Flaxon"
    }

@app.get("/html")
async def html():

    return HTMLResponse(
        "<h1>Hello</h1>"
    )

@app.get("/download")
async def download():

    return FileResponse(
        "downloads/manual.pdf"
    )

@app.get("/redirect")
async def redirect():

    return RedirectResponse("/")

@app.get("/stream")
async def stream():

    async def generator():

        for i in range(10):
            yield f"{i}\n".encode()

    return StreamingResponse(
        generator(),
        media_type="text/plain",
    )

@app.get("/custom")
async def custom():

    return JSONResponse(
        {
            "status": "accepted"
        },
        status_code=202,
        headers={
            "X-Powered-By": "Flaxon"
        },
    )
```

---

# Best Practices

- Return dictionaries for JSON APIs.
- Use response classes only when additional control is needed.
- Stream large files instead of loading them into memory.
- Prefer `FileResponse` for downloads.
- Use proper HTTP status codes.
- Set cache headers when appropriate.
- Compress large responses.
- Use redirects instead of duplicate routes.
- Set secure cookies for authentication.
- Create custom response classes for reusable formats such as CSV, XML, or PDF.
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
