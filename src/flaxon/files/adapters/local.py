from __future__ import annotations

import shutil
from pathlib import Path


class LocalStorageAdapter:
    """Local storage adapter implementation for the files subsystem."""

    def __init__(self, base_path: str = "uploads") -> None:
        self.base_path = Path(base_path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        return self.base_path / path

    def write(self, path: str, data: bytes) -> None:
        """Perform the write operation for local storage adapter."""
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with Path(full_path).open("wb") as f:
            f.write(data)

    def read(self, path: str) -> bytes:
        """Perform the read operation for local storage adapter."""
        full_path = self._get_full_path(path)
        with Path(full_path).open("rb") as f:
            return f.read()

    def delete(self, path: str) -> bool:
        """Delete the specified entry from the configured store."""
        full_path = self._get_full_path(path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def exists(self, path: str) -> bool:
        """Return whether the requested entry exists."""
        return self._get_full_path(path).exists()

    def size(self, path: str) -> int:
        """Perform the size operation for local storage adapter."""
        full_path = self._get_full_path(path)
        if full_path.exists():
            return full_path.stat().st_size
        return 0

    def list(self, path: str = "") -> list[str]:
        """Return the matching entries."""
        full_path = self.base_path / path
        if not full_path.exists():
            return []

        result = []
        for item in full_path.iterdir():
            rel_path = str(item.relative_to(self.base_path))
            result.append(rel_path)
        return result

    def move(self, source: str, destination: str) -> None:
        """Perform the move operation for local storage adapter."""
        src_path = self._get_full_path(source)
        dst_path = self._get_full_path(destination)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

    def copy(self, source: str, destination: str) -> None:
        """Return a copy of the current value."""
        src_path = self._get_full_path(source)
        dst_path = self._get_full_path(destination)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_path), str(dst_path))

    def get_url(self, path: str, base_url: str = "/uploads") -> str:
        """Return the url."""
        return f"{base_url}/{path}"
