"""
HTTP streaming support for Flaxon.

This module provides utilities for streaming responses and request bodies.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

from flaxon._imports import import_module

from .response import StreamingResponse


class Stream:
    """
    Streaming utility class.

    This class provides utilities for creating streaming responses.
    """

    @staticmethod
    def from_iterable(iterable: Iterator[bytes]) -> StreamingResponse:
        """
        Create a streaming response from an iterable.

        Args:
            iterable: An iterable of byte chunks.

        Returns:
            A streaming response.
        """
        return StreamingResponse(iterable)

    @staticmethod
    def from_async_iterable(iterable: AsyncIterator[bytes]) -> StreamingResponse:
        """
        Create a streaming response from an async iterable.

        Args:
            iterable: An async iterable of byte chunks.

        Returns:
            A streaming response.
        """
        return StreamingResponse(iterable)

    @staticmethod
    def from_generator(generator: Callable[[], Iterator[bytes]]) -> StreamingResponse:
        """
        Create a streaming response from a generator function.

        Args:
            generator: A generator function that yields byte chunks.

        Returns:
            A streaming response.
        """
        return StreamingResponse(generator())

    @staticmethod
    def from_async_generator(
        generator: Callable[[], AsyncIterator[bytes]],
    ) -> StreamingResponse:
        """
        Create a streaming response from an async generator function.

        Args:
            generator: An async generator function that yields byte chunks.

        Returns:
            A streaming response.
        """
        return StreamingResponse(generator())

    @staticmethod
    def file(path: str, chunk_size: int = 8192) -> StreamingResponse:
        """
        Create a streaming response from a file.

        Args:
            path: The file path.
            chunk_size: The chunk size in bytes.

        Returns:
            A streaming response.
        """

        async def stream_file() -> AsyncIterator[bytes]:
            aiofiles = import_module("aiofiles")

            async with aiofiles.open(path, "rb") as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(stream_file())

    @staticmethod
    def text(text: str, chunk_size: int = 8192) -> StreamingResponse:
        """
        Create a streaming response from text.

        Args:
            text: The text to stream.
            chunk_size: The chunk size in bytes.

        Returns:
            A streaming response.
        """

        async def stream_text() -> AsyncIterator[bytes]:
            for i in range(0, len(text), chunk_size):
                yield text[i : i + chunk_size].encode("utf-8")

        return StreamingResponse(stream_text())

    @staticmethod
    def json_lines(data: list[Any]) -> StreamingResponse:
        """
        Create a streaming response with JSON lines format.

        Args:
            data: A list of objects to stream as JSON lines.

        Returns:
            A streaming response.
        """

        async def stream_json_lines() -> AsyncIterator[bytes]:
            for item in data:
                yield json.dumps(item).encode("utf-8") + b"\n"

        return StreamingResponse(stream_json_lines(), media_type="application/x-ndjson")

    @staticmethod
    def sse(events: AsyncIterator[dict[str, Any]]) -> StreamingResponse:
        """
        Create a Server-Sent Events streaming response.

        Args:
            events: An async iterator of event dictionaries.

        Returns:
            A streaming response.
        """

        async def stream_sse() -> AsyncIterator[bytes]:
            async for event in events:
                data = event.get("data", "")
                event_type = event.get("event", "")
                event_id = event.get("id", "")

                if event_type:
                    yield f"event: {event_type}\n".encode()
                if event_id:
                    yield f"id: {event_id}\n".encode()

                for line in data.split("\n"):
                    yield f"data: {line}\n".encode()

                yield b"\n"
                await asyncio.sleep(0.01)

        return StreamingResponse(stream_sse(), media_type="text/event-stream")


class RequestStream:
    """
    Request body streaming utility.

    This class provides utilities for streaming request bodies.
    """

    def __init__(self, request: Any) -> None:
        """
        Initialize the request stream.

        Args:
            request: The request object.
        """
        self.request = request
        self._receive = request._receive
        self._body_read = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """
        Iterate over the request body chunks.

        Yields:
            Chunks of the request body.
        """
        if self._body_read:
            return

        more_body = True
        while more_body:
            message = await self._receive()
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue

            body = message.get("body", b"")
            if body:
                yield body

            more_body = bool(message.get("more_body", False))

        self._body_read = True

    async def read_chunks(self, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """
        Read the request body in chunks.

        Args:
            chunk_size: The chunk size in bytes.

        Yields:
            Chunks of the request body.
        """
        buffer = b""

        async for chunk in self:
            buffer += chunk
            while len(buffer) >= chunk_size:
                yield buffer[:chunk_size]
                buffer = buffer[chunk_size:]

        if buffer:
            yield buffer
