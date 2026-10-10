from __future__ import annotations

import mimetypes
from collections.abc import AsyncIterator
from pathlib import Path

from flaxon._imports import import_module
from flaxon.http import StreamingResponse


class FileStreamer:
    """File streamer implementation for the files subsystem."""

    def __init__(self, chunk_size: int = 8192) -> None:
        self.chunk_size = chunk_size

    async def stream_file(self, path: str) -> AsyncIterator[bytes]:
        """Perform the stream file operation for file streamer."""
        with Path(path).open("rb") as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk

    async def stream_file_async(self, path: str) -> AsyncIterator[bytes]:
        """Perform the stream file async operation for file streamer."""
        try:
            aiofiles = import_module("aiofiles")

            async with aiofiles.open(path, "rb") as f:
                while True:
                    chunk = await f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except ImportError:
            async for chunk in self.stream_file(path):
                yield chunk

    def create_response(self, path: str, filename: str | None = None) -> StreamingResponse:
        """Create the response."""
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or "application/octet-stream"

        headers = {}
        if filename:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return StreamingResponse(
            self.stream_file(path),
            media_type=mime_type,
            headers=headers,
        )

    def create_response_async(self, path: str, filename: str | None = None) -> StreamingResponse:
        """Create the response async."""
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or "application/octet-stream"

        headers = {}
        if filename:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return StreamingResponse(
            self.stream_file_async(path),
            media_type=mime_type,
            headers=headers,
        )

    def get_file_info(self, path: str) -> dict[str, str | int]:
        """Return the file info."""
        stat = Path(path).stat()
        return {
            "size": stat.st_size,
            "mime_type": self._guess_mime_type(path),
            "filename": Path(path).name,
        }

    def _guess_mime_type(self, path: str) -> str:

        mime, _ = mimetypes.guess_type(path)
        return mime or "application/octet-stream"

    def is_path_safe(self, path: str, base_dir: str) -> bool:
        """Return whether path safe holds for the current value."""
        try:
            resolved_path = Path(path).resolve()
            resolved_base = Path(base_dir).resolve()
            return resolved_path.is_relative_to(resolved_base)
        except ValueError:
            return False
