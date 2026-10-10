from __future__ import annotations

import mimetypes
from typing import Any, ClassVar

from flaxon._imports import import_attribute

from .upload import UploadedFile


class FileValidator:
    """File validator implementation for the files subsystem."""

    def __init__(
        self,
        max_size: int | None = None,
        allowed_extensions: list[str] | None = None,
        allowed_mime_types: list[str] | None = None,
        min_size: int | None = None,
    ) -> None:
        self.max_size = max_size
        self.min_size = min_size
        self.allowed_extensions = {ext.lower() for ext in (allowed_extensions or [])}
        self.allowed_mime_types = {mime.lower() for mime in (allowed_mime_types or [])}

    def validate(self, file: UploadedFile) -> list[str]:
        """Check the supplied value against the configured constraints."""
        errors = []

        if self.max_size is not None and file.size > self.max_size:
            errors.append(f"File size {file.size} exceeds maximum of {self.max_size} bytes")

        if self.min_size is not None and file.size < self.min_size:
            errors.append(f"File size {file.size} is below minimum of {self.min_size} bytes")

        if self.allowed_extensions:
            ext = file.extension.lower()
            if ext not in self.allowed_extensions:
                errors.append(f"File extension '{ext}' is not allowed")

        if self.allowed_mime_types:
            mime = file.content_type.lower()
            if mime not in self.allowed_mime_types:
                errors.append(f"File type '{mime}' is not allowed")

        return errors

    def is_valid(self, file: UploadedFile) -> bool:
        """Return whether valid holds for the current value."""
        return len(self.validate(file)) == 0

    def validate_many(self, files: list[UploadedFile]) -> dict[str, list[str]]:
        """Validate the many."""
        errors = {}
        for i, file in enumerate(files):
            file_errors = self.validate(file)
            if file_errors:
                errors[f"file_{i}"] = file_errors
        return errors

    def get_extension_from_mime(self, mime_type: str) -> str | None:
        """Return the extension from mime."""
        ext = mimetypes.guess_extension(mime_type)
        return ext[1:] if ext else None

    def get_mime_from_extension(self, extension: str) -> str | None:
        """Return the mime from extension."""
        mime, _ = mimetypes.guess_type(f"file.{extension}")
        return mime


class ImageValidator(FileValidator):
    """Image validator implementation for the files subsystem."""

    IMAGE_MIME_TYPES: ClassVar[Any] = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "image/bmp",
        "image/tiff",
    }

    IMAGE_EXTENSIONS: ClassVar[Any] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff"}

    def __init__(
        self,
        max_size: int | None = 10 * 1024 * 1024,
        max_width: int | None = None,
        max_height: int | None = None,
        min_width: int | None = None,
        min_height: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            max_size=max_size,
            allowed_extensions=list(self.IMAGE_EXTENSIONS),
            allowed_mime_types=list(self.IMAGE_MIME_TYPES),
            **kwargs,
        )
        self.max_width = max_width
        self.max_height = max_height
        self.min_width = min_width
        self.min_height = min_height

    def validate_image(self, file: UploadedFile) -> list[str]:
        """Validate the image."""
        errors = self.validate(file)

        try:
            image_type = import_attribute("PIL", "Image")

            image = image_type.open(file.file)
            width, height = image.size

            if self.max_width is not None and width > self.max_width:
                errors.append(f"Image width {width} exceeds maximum of {self.max_width}")
            if self.max_height is not None and height > self.max_height:
                errors.append(f"Image height {height} exceeds maximum of {self.max_height}")
            if self.min_width is not None and width < self.min_width:
                errors.append(f"Image width {width} is below minimum of {self.min_width}")
            if self.min_height is not None and height < self.min_height:
                errors.append(f"Image height {height} is below minimum of {self.min_height}")

        except ImportError:
            pass
        except Exception:
            errors.append("Invalid image file")

        return errors
