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
        self._headers: Headers | None = None
        self._cookies: Cookies | None = None
        self._query: dict[str, str] | None = None
        self.path_params: dict[str, Any] = dict(scope.get("path_params", {}))
        self.user = scope.get("user")
        self._body: bytes | None = None
        self._session = None if getattr(self.app, "sessions", None) is not None else scope.get("session")

    @property
    def headers(self) -> Headers:
        """Materialize a mutable header mapping once, when accessed."""
        if self._headers is None:
            self._headers = Headers(self.scope.get("headers", []))
        return self._headers

    @headers.setter
    def headers(self, value: Headers) -> None:
        self._headers = value

    @property
    def cookies(self) -> Cookies:
        """Decode cookies only when a handler or middleware uses them."""
        if self._cookies is None:
            data = {}
            if self._headers is None:
                values = [
                    v.decode("latin-1") for k, v in self.scope.get("headers", []) if k.lower() == b"cookie"
                ]
                raw = "; ".join(values)
            else:
                raw = self._headers.get("cookie", "")
            for item in raw.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    data[key] = value
            self._cookies = Cookies(data)
        return self._cookies

    @cookies.setter
    def cookies(self, value: Cookies) -> None:
        self._cookies = value

    @property
    def query(self) -> dict[str, str]:
        """Parse query values once and retain the historical first-value rule."""
        if self._query is None:
            raw = self.scope.get("query_string", b"")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            self._query = {key: values[0] for key, values in parse_qs(raw, keep_blank_values=True).items()}
        return self._query

    @query.setter
    def query(self, value: dict[str, str]) -> None:
        self._query = value

    @property
    def query_params(self) -> dict[str, str]:
        """Alias the same cached query mapping."""
        return self.query

    @query_params.setter
    def query_params(self, value: dict[str, str]) -> None:
        self.query = value

    @property
    def session(self) -> Any:
        """Create an unsaved session on first access; persist only mutations."""
        if self._session is None:
            from flaxon.sessions.session import Session

            manager = getattr(self.app, "sessions", None)
            self._session = Session(ttl=getattr(manager, "ttl", 86400))
        return self._session

    @session.setter
    def session(self, value: Any) -> None:
        self._session = value

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
