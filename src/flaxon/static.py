"""Static file serving for Flaxon.

Example:
    app.mount_static("/static", "static")
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from .exceptions import NotFound
from .http import Request, Response


class StaticFiles:
    """Serves files from a directory over HTTP.

    Paths are resolved safely against `directory` -- requests that would
    escape it (e.g. via `..` segments) are rejected with 404 rather than
    reading files outside the served directory.
    """

    def __init__(self, directory: str | Path, cache_control: str | None = "public, max-age=3600") -> None:
        self.directory = Path(directory).resolve()
        self.cache_control = cache_control

    async def __call__(self, request: Request, filepath: str) -> Response:
        target = (self.directory / filepath).resolve()

        try:
            target.relative_to(self.directory)
        except ValueError:
            raise NotFound("File not found.") from None

        if not target.is_file():
            raise NotFound("File not found.")

        content_type, _ = mimetypes.guess_type(str(target))
        content = target.read_bytes()

        headers = {}
        if self.cache_control:
            headers["cache-control"] = self.cache_control

        return Response(content, media_type=content_type or "application/octet-stream", headers=headers)
