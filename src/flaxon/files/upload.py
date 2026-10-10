from __future__ import annotations

import logging
import mimetypes
import re
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from flaxon.exceptions import BadRequest


@dataclass
class UploadedFile:
    """Uploaded file implementation for the files subsystem."""

    filename: str
    content_type: str
    size: int
    file: BinaryIO
    field_name: str | None = None

    async def read(self, size: int = -1) -> bytes:
        """Perform the read operation for uploaded file."""
        if hasattr(self.file, "read"):
            return self.file.read(size)
        return b""

    async def seek(self, offset: int, whence: int = 0) -> int:
        """Perform the seek operation for uploaded file."""
        if hasattr(self.file, "seek"):
            return self.file.seek(offset, whence)
        return 0

    async def close(self) -> None:
        """Release the resources held by this object."""
        if hasattr(self.file, "close"):
            self.file.close()

    def save(self, path: str) -> None:
        """Persist the supplied value using the configured storage."""
        if hasattr(self.file, "seek"):
            self.file.seek(0)

        with Path(path).open("wb") as f:
            if hasattr(self.file, "read"):
                while True:
                    chunk = self.file.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            else:
                f.write(self.file.read())

    @property
    def extension(self) -> str:
        """Return the configured extension."""
        ext = mimetypes.guess_extension(self.content_type)
        if ext:
            return ext
        if "." in self.filename:
            return self.filename.rsplit(".", 1)[-1]
        return ""

    @property
    def safe_filename(self) -> str:
        """Return the configured safe filename."""
        return re.sub(r"[^a-zA-Z0-9._-]", "_", self.filename)


class FileUpload:
    """File upload implementation for the files subsystem."""

    def __init__(self, max_size: int = 100 * 1024 * 1024, max_files: int = 10) -> None:
        self.max_size = max_size
        self.max_files = max_files

    async def parse(self, request: Any) -> list[UploadedFile]:
        """Parse the supplied input into its structured representation."""
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type:
            raise BadRequest("Content-Type must be multipart/form-data")

        boundary = self._extract_boundary(content_type)
        if not boundary:
            raise BadRequest("Invalid multipart content type")

        body = await request.body()
        if not body:
            return []

        return await self._parse_multipart(body, boundary)

    def _extract_boundary(self, content_type: str) -> str | None:

        match = re.search(r'boundary="?([^";]+)"?', content_type)
        if match:
            return match.group(1)
        return None

    async def _parse_multipart(self, data: bytes, boundary: str) -> list[UploadedFile]:
        boundary_bytes = f"--{boundary}".encode()
        parts = data.split(boundary_bytes)

        files = []

        for raw_part in parts:
            part = raw_part
            if not part or part in {b"--\r\n", b"--"}:
                continue

            part = part.strip(b"\r\n")
            if not part:
                continue

            headers, content = self._split_headers_content(part)

            if self._is_file(headers):
                filename = self._get_filename(headers)
                content_type = self._get_content_type(headers)
                field_name = self._get_field_name(headers)

                with ExitStack() as stack:
                    file_obj = stack.enter_context(tempfile.NamedTemporaryFile(delete=False))
                    file_obj.write(content)
                    file_obj.flush()
                    file_obj.seek(0)

                    uploaded_file = UploadedFile(
                        filename=filename,
                        content_type=content_type,
                        size=len(content),
                        file=file_obj,
                        field_name=field_name,
                    )
                    files.append(uploaded_file)
                    # UploadedFile owns the open handle after successful parsing.
                    stack.pop_all()

        return files

    def _split_headers_content(self, part: bytes) -> tuple[list[bytes], bytes]:
        parts = part.split(b"\r\n\r\n", 1)
        if len(parts) == 2:
            return parts[0].split(b"\r\n"), parts[1]
        return [], parts[0]

    def _get_field_name(self, headers: list[bytes]) -> str | None:

        for header in headers:
            if header.lower().startswith(b"content-disposition:"):
                match = re.search(rb'name="([^"]+)"', header)
                if match:
                    return match.group(1).decode("utf-8")
        return None

    def _is_file(self, headers: list[bytes]) -> bool:
        for header in headers:
            if header.lower().startswith(b"content-disposition:") and b"filename=" in header:
                return True
        return False

    def _get_filename(self, headers: list[bytes]) -> str:

        for header in headers:
            if header.lower().startswith(b"content-disposition:"):
                match = re.search(rb'filename="([^"]+)"', header)
                if match:
                    return match.group(1).decode("utf-8")
        return "uploaded_file"

    def _get_content_type(self, headers: list[bytes]) -> str:
        for header in headers:
            if header.lower().startswith(b"content-type:"):
                return header.split(b":", 1)[1].strip().decode("utf-8")
        return "application/octet-stream"

    async def cleanup(self, files: list[UploadedFile]) -> None:
        """Perform the cleanup operation for file upload."""
        for file in files:
            try:
                if hasattr(file.file, "name"):
                    path = file.file.name
                    file.close()
                    if Path(path).exists():
                        Path(path).unlink()
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolated callback or cleanup failed (%s)", type(exc).__name__
                )
