"""
Request body handling for Flaxon.

This module provides utilities for handling request bodies of various types.
"""

from __future__ import annotations

import gzip
import json
import zlib
from collections.abc import Mapping
from typing import Any, Protocol

from flaxon.exceptions import BadRequest


class _ReadableRequest(Protocol):
    @property
    def headers(self) -> Mapping[str, str]: ...

    async def body(self) -> bytes: ...

    async def text(self) -> str: ...

    async def json(self) -> Any: ...


class BodyParser:
    """
    Request body parser.

    This class provides utilities for parsing request bodies of various
    content types and encodings.
    """

    @staticmethod
    async def parse_json(request: _ReadableRequest) -> Any:
        """
        Parse JSON body.

        Args:
            request: The request object.

        Returns:
            The parsed JSON data.

        Raises:
            BadRequest: If the body is not valid JSON.
        """
        try:
            return await request.json()
        except json.JSONDecodeError as exc:
            raise BadRequest("Invalid JSON body") from exc

    @staticmethod
    async def parse_text(request: _ReadableRequest) -> str:
        """
        Parse text body.

        Args:
            request: The request object.

        Returns:
            The body as text.
        """
        return await request.text()

    @staticmethod
    async def parse_bytes(request: _ReadableRequest) -> bytes:
        """
        Parse bytes body.

        Args:
            request: The request object.

        Returns:
            The body as bytes.
        """
        return await request.body()

    @staticmethod
    async def parse_form(request: _ReadableRequest) -> dict[str, Any]:
        """
        Parse form data.

        Args:
            request: The request object.

        Returns:
            The parsed form data.

        Raises:
            BadRequest: If the content type is not form data.
        """
        from .form import FormData

        form = await FormData.from_request(request)
        data: dict[str, Any] = form.to_dict()
        return data

    @staticmethod
    async def parse_multipart(request: _ReadableRequest) -> dict[str, Any]:
        """
        Parse multipart data.

        Args:
            request: The request object.

        Returns:
            The parsed multipart data.

        Raises:
            BadRequest: If the content type is not multipart.
        """
        from .form import FormData

        form = await FormData.from_request(request)
        data: dict[str, Any] = form.to_dict()
        return data


class BodyDecoder:
    """
    Request body decoder.

    This class provides utilities for decoding request bodies with
    various content encodings.
    """

    @staticmethod
    async def decode(request: _ReadableRequest, body: bytes | None = None) -> bytes:
        """
        Decode a request body.

        Args:
            request: The request object.
            body: The body bytes (fetches from request if not provided).

        Returns:
            The decoded body.

        Raises:
            BadRequest: If the encoding is not supported.
        """
        if body is None:
            body = await request.body()

        content_encoding = request.headers.get("content-encoding", "").lower()

        if content_encoding == "gzip":
            try:
                return gzip.decompress(body)
            except (OSError, EOFError, zlib.error) as exc:
                raise BadRequest("Invalid gzip body") from exc

        if content_encoding == "deflate":
            try:
                return zlib.decompress(body)
            except zlib.error as exc:
                raise BadRequest("Invalid deflate body") from exc

        if content_encoding and content_encoding not in {"identity", ""}:
            raise BadRequest(f"Unsupported content encoding: {content_encoding}")

        return body

    @staticmethod
    async def decode_json(request: _ReadableRequest) -> Any:
        """
        Decode and parse JSON body.

        Args:
            request: The request object.

        Returns:
            The parsed JSON data.

        Raises:
            BadRequest: If the body is not valid JSON.
        """
        body = await BodyDecoder.decode(request)
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise BadRequest("Invalid JSON body") from exc

    @staticmethod
    async def decode_text(request: _ReadableRequest) -> str:
        """
        Decode and parse text body.

        Args:
            request: The request object.

        Returns:
            The body as text.

        Raises:
            BadRequest: If the body cannot be decoded.
        """
        body = await BodyDecoder.decode(request)
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BadRequest("Body cannot be decoded as UTF-8") from exc


class BodyLimiter:
    """
    Request body limiter.

    This class provides utilities for limiting request body sizes.
    """

    def __init__(self, max_size: int = 10 * 1024 * 1024) -> None:
        """
        Initialize the body limiter.

        Args:
            max_size: The maximum body size in bytes.
        """
        self.max_size = max_size

    async def check(self, request: _ReadableRequest) -> None:
        """
        Check if the request body exceeds the maximum size.

        Args:
            request: The request object.

        Raises:
            BadRequest: If the body is too large.
        """
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    raise BadRequest(f"Request body too large: {size} bytes (max: {self.max_size})")
            except ValueError:
                pass

    async def read_limited(self, request: _ReadableRequest) -> bytes:
        """
        Read the request body with size limiting.

        Args:
            request: The request object.

        Returns:
            The body bytes.

        Raises:
            BadRequest: If the body is too large.
        """
        await self.check(request)

        body = await request.body()

        if len(body) > self.max_size:
            raise BadRequest(f"Request body too large: {len(body)} bytes (max: {self.max_size})")

        return body
