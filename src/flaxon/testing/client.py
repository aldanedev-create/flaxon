from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit


@dataclass
class TestResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.content)


class AsyncTestClient:

    def __init__(self, app: Any, base_url: str = "http://testserver") -> None:
        self.app = app
        self.base_url = base_url.rstrip("/")

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_data: Any = None,
        content: bytes | str | None = None,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
    ) -> TestResponse:
        url = urlsplit(f"{self.base_url}{path}")
        query_string = url.query
        if query:
            query_string = urlencode(query, doseq=True)

        raw_headers = [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in (headers or {}).items()
        ]
        raw_headers.append((b"host", url.netloc.encode("latin-1")))

        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            raw_headers.append((b"content-type", b"application/json"))
        elif isinstance(content, str):
            body = content.encode("utf-8")
        else:
            body = content or b""

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.5"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": url.scheme,
            "path": url.path or "/",
            "raw_path": (url.path or "/").encode("ascii"),
            "query_string": query_string.encode("utf-8"),
            "headers": raw_headers,
            "client": ("127.0.0.1", 12345),
            "server": (url.hostname or "testserver", url.port or 80),
        }

        received = False
        messages: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            nonlocal received
            if not received:
                received = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            await asyncio.sleep(0)
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        await self.app(scope, receive, send)

        start = next(
            message
            for message in messages
            if message["type"] == "http.response.start"
        )
        chunks = [
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        ]

        response_headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in start.get("headers", [])
        }

        return TestResponse(
            start["status"], response_headers, b"".join(chunks)
        )

    async def get(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("DELETE", path, **kwargs)

    async def options(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("OPTIONS", path, **kwargs)

    async def head(self, path: str, **kwargs: Any) -> TestResponse:
        return await self.request("HEAD", path, **kwargs)


class TestClient:
    __test__ = False

    def __init__(self, app: Any, base_url: str = "http://testserver") -> None:
        self.async_client = AsyncTestClient(app, base_url)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _run(self, coroutine: Any) -> Any:
        """Reuse one event loop for sync calls instead of creating one per request."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop.run_until_complete(coroutine)
        # Preserve a useful error when the sync client is used inside async code.
        coroutine.close()
        raise RuntimeError("TestClient cannot make sync requests from a running event loop; use AsyncTestClient")

    def request(self, method: str, path: str, **kwargs: Any) -> TestResponse:
        return self._run(self.async_client.request(method, path, **kwargs))

    def close(self) -> None:
        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()

    def __del__(self) -> None:
        try:
            self.close()
        except (RuntimeError, AttributeError):
            # Best-effort finalizer; explicit close() still reports errors.
            pass

    def get(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("DELETE", path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("OPTIONS", path, **kwargs)

    def head(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("HEAD", path, **kwargs)
