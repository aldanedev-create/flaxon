"""
File upload handling for Flaxon.

This module provides utilities for handling file uploads from multipart form data.
"""

from __future__ import annotations

import io
import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from flaxon.exceptions import BadRequest


@dataclass
class UploadedFile:
    """
    Uploaded file from multipart form data.

    Attributes:
        filename: The original filename.
        content_type: The file content type.
        size: The file size in bytes.
        file: The file-like object.
    """

    filename: str
    content_type: str
    size: int
    file: BinaryIO

    async def read(self, size: int = -1) -> bytes:
        """
        Read the file content.

        Args:
            size: The number of bytes to read.

        Returns:
            The file content as bytes.
        """
        if hasattr(self.file, "read"):
            return self.file.read(size)
        return b""

    async def seek(self, offset: int, whence: int = 0) -> int:
        """
        Seek within the file.

        Args:
            offset: The offset to seek to.
            whence: The seek whence.

        Returns:
            The new position.
        """
        if hasattr(self.file, "seek"):
            return self.file.seek(offset, whence)
        return 0

    async def close(self) -> None:
        """Close the file."""
        if hasattr(self.file, "close"):
            self.file.close()

    def save(self, path: str) -> None:
        """
        Save the file to disk.

        Args:
            path: The path to save to.
        """
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
        """Get the file extension."""
        ext = mimetypes.guess_extension(self.content_type)
        if ext:
            return ext
        if "." in self.filename:
            return self.filename.rsplit(".", 1)[-1]
        return ""

    @property
    def safe_filename(self) -> str:
        """Get a safe version of the filename."""
        return re.sub(r"[^a-zA-Z0-9._-]", "_", self.filename)


class MultipartParser:
    """
    Multipart form data parser.

    This class parses multipart/form-data requests.
    """

    def __init__(self, content_type: str) -> None:
        """
        Initialize the parser.

        Args:
            content_type: The content type header.
        """
        self.boundary = self._extract_boundary(content_type)
        if not self.boundary:
            raise BadRequest("Invalid multipart content type: missing boundary")

    def _extract_boundary(self, content_type: str) -> str | None:
        """Extract the boundary from the content type."""
        match = re.search(r'boundary="?([^";]+)"?', content_type)
        if match:
            return match.group(1)
        return None

    async def parse(self, request: Any) -> dict[str, list[str] | UploadedFile]:
        """
        Parse multipart form data.

        Args:
            request: The request object.

        Returns:
            A dictionary of form fields.
        """
        body = await request.body()
        if not body:
            return {}

        return self._parse_bytes(body)

    def _parse_bytes(self, data: bytes) -> dict[str, list[str] | UploadedFile]:
        """
        Parse multipart bytes.

        Args:
            data: The multipart data.

        Returns:
            A dictionary of form fields.
        """
        boundary = f"--{self.boundary}".encode()
        parts = data.split(boundary)

        result: dict[str, list[str] | UploadedFile] = {}

        for raw_part in parts:
            part = raw_part
            if not part or part in {b"--\r\n", b"--"}:
                continue

            part = part.strip(b"\r\n")
            if not part:
                continue

            headers, content = self._split_headers_content(part)
            field_name = self._get_field_name(headers)

            if not field_name:
                continue

            if self._is_file(headers):
                uploaded_file = self._create_uploaded_file(headers, content)
                result[field_name] = uploaded_file
            else:
                value = content.decode("utf-8").strip()
                if field_name in result:
                    if isinstance(result[field_name], list):
                        result[field_name].append(value)
                    else:
                        result[field_name] = [str(result[field_name]), value]
                else:
                    result[field_name] = value

        return result

    def _split_headers_content(self, part: bytes) -> tuple[list[bytes], bytes]:
        """Split a part into headers and content."""
        parts = part.split(b"\r\n\r\n", 1)
        if len(parts) == 2:
            return parts[0].split(b"\r\n"), parts[1]
        return [], parts[0]

    def _get_field_name(self, headers: list[bytes]) -> str | None:
        """Extract the field name from headers."""
        for header in headers:
            if header.lower().startswith(b"content-disposition:"):
                match = re.search(rb'name="([^"]+)"', header)
                if match:
                    return match.group(1).decode("utf-8")
        return None

    def _is_file(self, headers: list[bytes]) -> bool:
        """Check if the part is a file."""
        for header in headers:
            if header.lower().startswith(b"content-disposition:") and b"filename=" in header:
                return True
        return False

    def _get_filename(self, headers: list[bytes]) -> str:
        """Extract the filename from headers."""
        for header in headers:
            if header.lower().startswith(b"content-disposition:"):
                match = re.search(rb'filename="([^"]+)"', header)
                if match:
                    return match.group(1).decode("utf-8")
        return "uploaded_file"

    def _get_content_type(self, headers: list[bytes]) -> str:
        """Extract the content type from headers."""
        for header in headers:
            if header.lower().startswith(b"content-type:"):
                return header.split(b":", 1)[1].strip().decode("utf-8")
        return "application/octet-stream"

    def _create_uploaded_file(self, headers: list[bytes], content: bytes) -> UploadedFile:
        """Create an UploadedFile from headers and content."""
        filename = self._get_filename(headers)
        content_type = self._get_content_type(headers)

        file_obj = io.BytesIO(content)
        return UploadedFile(
            filename=filename,
            content_type=content_type,
            size=len(content),
            file=file_obj,
        )


class FileStorage:
    """
    File storage utility.

    This class provides utilities for storing uploaded files.
    """

    def __init__(self, upload_dir: str = "uploads", max_size: int = 100 * 1024 * 1024) -> None:
        """
        Initialize the file storage.

        Args:
            upload_dir: The upload directory.
            max_size: The maximum file size in bytes.
        """
        self.upload_dir = upload_dir
        self.max_size = max_size
        self._ensure_upload_dir()

    def _ensure_upload_dir(self) -> None:
        """Create the upload directory if it doesn't exist."""
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)

    def save(self, uploaded_file: UploadedFile, filename: str | None = None) -> str:
        """
        Save an uploaded file.

        Args:
            uploaded_file: The uploaded file.
            filename: The filename to save as (auto-generated if not provided).

        Returns:
            The path where the file was saved.

        Raises:
            ValueError: If the file is too large.
        """
        if uploaded_file.size > self.max_size:
            raise ValueError(f"File too large: {uploaded_file.size} bytes (max: {self.max_size})")

        if not filename:
            ext = uploaded_file.extension
            filename = f"{uuid.uuid4().hex}{ext}"

        path = str(Path(self.upload_dir) / filename)
        uploaded_file.save(path)
        return path
