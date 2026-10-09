from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from .upload import UploadedFile


class FileStorage:
    def __init__(self, base_path: str = "uploads", url_prefix: str = "/uploads") -> None:
        self.base_path = Path(base_path)
        self.url_prefix = url_prefix
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, path: str = "", filename: str | None = None) -> Path:
        # Normalize backslashes to forward slashes before resolving, so a
        # Windows-style traversal payload (e.g. "..\\outside") is treated
        # as a parent-directory reference regardless of the host OS --
        # pathlib.resolve() only treats backslash as a separator on
        # Windows, so without this a "..\\outside" payload would only be
        # caught on a Windows-hosted deployment, silently accepted (as a
        # literal, oddly-named subdirectory) everywhere else.
        safe_path = (path or "").replace("\\", "/")
        safe_filename = (filename or "").replace("\\", "/")
        candidate = self.base_path / safe_path / safe_filename
        resolved_base = self.base_path.resolve()
        resolved = candidate.resolve()
        if resolved != resolved_base and resolved_base not in resolved.parents:
            raise ValueError("File path escapes the storage root")
        return resolved

    def generate_filename(self, original_filename: str) -> str:
        ext = ""
        if "." in original_filename:
            ext = original_filename.rsplit(".", 1)[1]
            ext = f".{ext}" if ext else ""

        return f"{uuid.uuid4().hex}{ext}"

    def save(self, file: UploadedFile, path: str | None = None, filename: str | None = None) -> str:
        if filename is None:
            filename = self.generate_filename(file.filename)

        if path is None:
            path = ""

        full_path = self._safe_path(path, filename)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        file.save(str(full_path))
        return str(full_path)

    def save_bytes(self, data: bytes, filename: str, path: str | None = None) -> str:
        if path is None:
            path = ""

        full_path = self._safe_path(path, filename)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(data)

        return str(full_path)

    def delete(self, file_path: str) -> bool:
        try:
            path = (
                self._safe_path(
                    Path(file_path).relative_to(self.base_path).parent.as_posix(), Path(file_path).name
                )
                if Path(file_path).is_absolute()
                else self._safe_path(file_path)
            )
            if path.exists():
                path.unlink()
                return True
            return False
        except (OSError, ValueError):
            return False

    def delete_directory(self, directory: str) -> bool:
        try:
            path = self._safe_path(directory)
            if path.exists() and path.is_dir():
                shutil.rmtree(path)
                return True
            return False
        except (OSError, ValueError):
            return False

    def exists(self, file_path: str) -> bool:
        try:
            path = (
                self._safe_path(Path(file_path).relative_to(self.base_path).as_posix())
                if Path(file_path).is_absolute()
                else self._safe_path(file_path)
            )
        except ValueError:
            return False
        return path.exists()

    def get_size(self, file_path: str) -> int:
        path = (
            self._safe_path(Path(file_path).relative_to(self.base_path).as_posix())
            if Path(file_path).is_absolute()
            else self._safe_path(file_path)
        )
        if path.exists():
            return path.stat().st_size
        return 0

    def get_url(self, file_path: str) -> str:
        relative = Path(file_path).relative_to(self.base_path)
        return f"{self.url_prefix}/{relative.as_posix()}"

    def list_files(self, directory: str = "") -> list[str]:
        path = self._safe_path(directory)
        if not path.exists():
            return []

        return [str(p) for p in path.iterdir() if p.is_file()]

    def get_file_info(self, file_path: str) -> dict[str, Any]:
        try:
            path = (
                self._safe_path(Path(file_path).relative_to(self.base_path).as_posix())
                if Path(file_path).is_absolute()
                else self._safe_path(file_path)
            )
        except ValueError:
            return {}
        if not path.exists():
            return {}

        stat = path.stat()
        return {
            "name": path.name,
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "path": str(path),
            "extension": path.suffix,
        }

    def create_thumbnail(self, file_path: str, size: tuple[int, int] = (320, 240)) -> str | None:
        """Create a bounded JPEG thumbnail beside a stored image when Pillow is available."""
        try:
            from PIL import Image

            source = (
                self._safe_path(Path(file_path).relative_to(self.base_path).as_posix())
                if Path(file_path).is_absolute()
                else self._safe_path(file_path)
            )
            thumbnail_path = self._safe_path("thumbnails", f"{source.stem}.jpg")
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as image:
                image.thumbnail(size)
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                image.save(thumbnail_path, format="JPEG", optimize=True)
            return str(thumbnail_path)
        except (ImportError, OSError, ValueError):
            return None
