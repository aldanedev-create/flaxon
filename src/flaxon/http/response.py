"""ASGI response classes."""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, Iterable
from typing import Any

from .headers import Headers


class Response:
    """An HTTP response that can be sent directly as an ASGI application."""

    media_type = "text/plain; charset=utf-8"

    def __init__(
        self,
        content: bytes | str = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = content.encode("utf-8") if isinstance(content, str) else content
        self.headers = Headers(headers or {})
        self.headers.setdefault("content-type", media_type or self.media_type)
        self.headers.setdefault("content-length", str(len(self.body)))

    @classmethod
    def from_value(cls, value: Any) -> Response:
        """Convert a conventional endpoint return value into a response."""
        if isinstance(value, Response):
            return value
        if value is None:
            return cls(status_code=204)
        if isinstance(value, (dict, list, tuple)):
            return JSONResponse(value)
        if isinstance(value, (str, bytes)):
            return cls(value)
        return JSONResponse(value)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": self.status_code, "headers": self.headers.to_asgi()})
        await send({"type": "http.response.body", "body": self.body, "more_body": False})


class JSONResponse(Response):
    """A JSON response."""

    media_type = "application/json; charset=utf-8"

    def __init__(self, content: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        super().__init__(
            json.dumps(content, ensure_ascii=False, default=_json_default),
            status_code,
            headers,
            self.media_type,
        )


def _json_default(value: Any) -> Any:
    """Serialize framework-supported model objects without hard dependencies."""
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return str(value)


class HTMLResponse(Response):
    """An HTML response."""

    media_type = "text/html; charset=utf-8"


class TextResponse(Response):
    """A text response."""


class RedirectResponse(Response):
    """A redirect response."""

    def __init__(self, url: str, status_code: int = 307, headers: dict[str, str] | None = None) -> None:
        values = dict(headers or {})
        values["location"] = url
        super().__init__(b"", status_code, values)


class StreamingResponse(Response):
    """A response that streams an iterable of byte chunks."""

    def __init__(self, content: AsyncIterable[bytes] | Iterable[bytes], status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self.content = content
        self.status_code = status_code
        self.headers = Headers(headers or {})
        self.headers.setdefault("content-type", self.media_type)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": self.status_code, "headers": self.headers.to_asgi()})
        if hasattr(self.content, "__aiter__"):
            async for chunk in self.content:  # type: ignore[union-attr]
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
        else:
            for chunk in self.content:  # type: ignore[union-attr]
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
