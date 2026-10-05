"""ASGI request wrapper."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

from .cookies import Cookies
from .headers import Headers
from .response import HTMLResponse


class Request:
    """Expose an ASGI HTTP request through a small, async-friendly API."""

    def __init__(self, scope: dict[str, Any], receive: Any, app: Any = None) -> None:
        self.scope = scope
        self._receive = receive
        self.app = app or scope.get("app")
        self.method = str(scope.get("method", "GET")).upper()
        self.path = str(scope.get("path", "/"))
        self.headers = Headers(scope.get("headers", []))
        self.path_params: dict[str, Any] = dict(scope.get("path_params", {}))
        self.user = scope.get("user")
        self._body: bytes | None = None
        cookie_data = {}
        for item in self.headers.get("cookie", "").split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookie_data[key] = value
        self.cookies = Cookies(cookie_data)

        raw_query = scope.get("query_string", b"")
        if isinstance(raw_query, bytes):
            raw_query = raw_query.decode("utf-8")
        parsed_query = parse_qs(raw_query, keep_blank_values=True)
        self.query: dict[str, str] = {key: values[0] for key, values in parsed_query.items()}
        self.query_params = self.query

    async def body(self) -> bytes:
        """Read and cache the complete request body."""
        if self._body is None:
            parts: list[bytes] = []
            while True:
                message = await self._receive()
                if message.get("type") != "http.request":
                    break
                parts.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            self._body = b"".join(parts)
        return self._body

    async def text(self, encoding: str = "utf-8") -> str:
        """Decode the request body as text."""
        return (await self.body()).decode(encoding)

    async def json(self) -> Any:
        """Decode the request body as JSON."""
        data = await self.body()
        return json.loads(data or b"null")

    async def form(self) -> Any:
        """Parse the request body as form data (urlencoded or multipart).

        Returns a FormData instance (see flaxon.http.form.FormData).
        """
        from .form import FormData

        return await FormData.from_request(self)

    async def render(self, template: str, context: dict[str, Any] | None = None) -> HTMLResponse:
        """Render a template using the application's configured engine."""
        if self.app is None or self.app.jinax is None:
            raise RuntimeError("No template engine configured")
        return HTMLResponse(await self.app.jinax.render(template, context or {}))

    async def compile(
        self,
        entry: str = "app.html",
        context: dict[str, Any] | None = None,
        *,
        title: str | None = None,
    ) -> HTMLResponse:
        """Render a startup-compiled Teloce HTML component as an SPA shell."""
        if self.app is None or self.app.teloce is None:
            raise RuntimeError("Teloce is not configured; call app.use_teloce() first")
        return self.app.teloce.render(entry, context, title=title)
