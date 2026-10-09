"""
Compression middleware for Flaxon.

This module provides response compression middleware using gzip and brotli.
"""

from __future__ import annotations

import gzip
import zlib
from typing import Any

from .base import Middleware


class CompressionMiddleware(Middleware):
    """
    Response compression middleware.

    This middleware compresses responses using gzip, deflate, or brotli
    based on the Accept-Encoding header.

    Example:
        ```python
        app.add_middleware(
            CompressionMiddleware,
            minimum_size=1024,
            compressible_types=["application/json", "text/html"],
        )
        ```
    """

    def __init__(
        self,
        app: Any,
        *,
        minimum_size: int = 1024,
        compressible_types: list[str] | None = None,
        level: int = 6,
    ) -> None:
        """
        Initialize the compression middleware.

        Args:
            app: The ASGI application.
            minimum_size: Minimum response size to compress.
            compressible_types: List of compressible content types.
            level: Compression level (1-9).
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_types = compressible_types or [
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/xhtml+xml",
            "application/rss+xml",
            "application/atom+xml",
            "application/ld+json",
            "application/x-www-form-urlencoded",
            "image/svg+xml",
        ]
        self.level = level

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process the request with compression."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        accept_encoding = self._get_accept_encoding(scope)
        encoding = self._choose_encoding(accept_encoding)

        if not encoding:
            await self.app(scope, receive, send)
            return

        body_parts: list[bytes] = []
        start_message: dict[str, Any] | None = None

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal start_message
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                content_type = self._get_content_type(headers)
                length = self._get_content_length(headers)
                already_encoded = any(key.lower() == b"content-encoding" for key, _ in headers)
                # Unknown-length streams pass through without buffering.
                if (length is not None and length >= self.minimum_size
                        and self._is_compressible(content_type)
                        and not content_type.startswith("text/event-stream")
                        and not already_encoded and scope.get("method") != "HEAD"
                        and message["status"] not in {204, 304}):
                    start_message = dict(message)
                    return
            elif message["type"] == "http.response.body" and start_message is not None:
                body_parts.append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                body = b"".join(body_parts)
                original = start_message.get("headers", [])
                if len(body) >= self.minimum_size:
                    body = self._compress(body, encoding)
                    vary = next((v.decode("latin-1") for k, v in original if k.lower() == b"vary"), "")
                    values = [value.strip() for value in vary.split(",") if value.strip()]
                    if not any(value.lower() in {"accept-encoding", "*"} for value in values):
                        values.append("Accept-Encoding")
                    start_message["headers"] = [
                        (k, v) for k, v in original
                        if k.lower() not in {b"content-length", b"content-encoding", b"vary"}
                    ] + [(b"content-length", str(len(body)).encode()),
                         (b"content-encoding", encoding.encode()),
                         (b"vary", ", ".join(values).encode("latin-1"))]
                await send(start_message)
                await send({"type": "http.response.body", "body": body, "more_body": False})
                start_message = None
                return
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _get_accept_encoding(self, scope: dict[str, Any]) -> str:
        for key, value in scope.get("headers", []):
            if key.lower() == b"accept-encoding":
                return value.decode("latin-1").lower()
        return ""

    def _choose_encoding(self, accept_encoding: str) -> str | None:
        encodings = [enc.strip() for enc in accept_encoding.split(",") if enc.strip()]

        if "br" in encodings:
            return "br"
        if "gzip" in encodings:
            return "gzip"
        if "deflate" in encodings:
            return "deflate"

        return None

    def _get_content_type(self, headers: list[tuple[bytes, bytes]]) -> str | None:
        for key, value in headers:
            if key.lower() == b"content-type":
                return value.decode("latin-1")
        return None

    def _get_content_length(self, headers: list[tuple[bytes, bytes]]) -> int | None:
        for key, value in headers:
            if key.lower() == b"content-length":
                try:
                    return int(value.decode("latin-1"))
                except ValueError:
                    return None
        return None

    def _is_compressible(self, content_type: str | None) -> bool:
        if not content_type:
            return False

        for pattern in self.compressible_types:
            if content_type.startswith(pattern):
                return True

        return False

    def _compress(self, data: bytes, encoding: str) -> bytes:
        if encoding == "gzip":
            return gzip.compress(data, compresslevel=self.level)

        if encoding == "deflate":
            return zlib.compress(data, level=self.level)

        if encoding == "br":
            try:
                import brotli

                return brotli.compress(data, quality=self.level)
            except ImportError:
                return data

        return data
