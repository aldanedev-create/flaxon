"""
Content type handling for Flaxon.

This module provides utilities for handling HTTP content types.
"""

from __future__ import annotations

import contextlib
import mimetypes
from typing import Any

from flaxon.exceptions import BadRequest


class ContentType:
    """Content type utilities."""

    APPLICATION_JSON = "application/json"
    APPLICATION_XML = "application/xml"
    APPLICATION_FORM = "application/x-www-form-urlencoded"
    MULTIPART_FORM = "multipart/form-data"
    TEXT_PLAIN = "text/plain"
    TEXT_HTML = "text/html"
    TEXT_XML = "text/xml"
    OCTET_STREAM = "application/octet-stream"
    EVENT_STREAM = "text/event-stream"
    NDJSON = "application/x-ndjson"

    @classmethod
    def parse(cls, content_type: str) -> dict[str, Any]:
        """Parse a content type header."""
        if not content_type:
            return {"type": "application", "subtype": "octet-stream", "parameters": {}}

        parts = content_type.split(";")
        main = parts[0].strip().split("/")

        if len(main) != 2:
            return {"type": "application", "subtype": "octet-stream", "parameters": {}}

        parameters: dict[str, str] = {}

        for part in parts[1:]:
            if "=" in part:
                key, value = part.strip().split("=", 1)
                parameters[key] = value.strip("\"'")

        return {
            "type": main[0].lower(),
            "subtype": main[1].lower(),
            "parameters": parameters,
        }

    @classmethod
    def matches(cls, content_type: str, pattern: str) -> bool:
        """
        Check if a content type matches a pattern.

        Args:
            content_type: The content type header value.
            pattern: The pattern to match against.

        Returns:
            True if the content type matches the pattern.

        Example:
        ```python
            ContentType.matches("application/json", "application/json")
            ContentType.matches("application/json", "application/*")
        ```
        """
        parsed = cls.parse(content_type)
        pattern_parts = pattern.split("/")

        if len(pattern_parts) != 2:
            return False

        pattern_type = pattern_parts[0]
        pattern_subtype = pattern_parts[1]

        if pattern_type != "*" and parsed["type"] != pattern_type:
            return False

        return not (pattern_subtype != "*" and parsed["subtype"] != pattern_subtype)

    @classmethod
    def is_json(cls, content_type: str) -> bool:
        """
        Check if a content type is JSON.

        Args:
            content_type: The content type header value.

        Returns:
            True if the content type is JSON.
        """
        return cls.matches(content_type, "application/json") or cls.matches(
            content_type, "application/*+json"
        )

    @classmethod
    def is_form(cls, content_type: str) -> bool:
        """
        Check if a content type is form data.

        Args:
            content_type: The content type header value.

        Returns:
            True if the content type is form data.
        """
        return cls.matches(content_type, "application/x-www-form-urlencoded")

    @classmethod
    def is_multipart(cls, content_type: str) -> bool:
        """
        Check if a content type is multipart form data.

        Args:
            content_type: The content type header value.

        Returns:
            True if the content type is multipart form data.
        """
        return cls.matches(content_type, "multipart/form-data")

    @classmethod
    def is_text(cls, content_type: str) -> bool:
        """
        Check if a content type is text.

        Args:
            content_type: The content type header value.

        Returns:
            True if the content type is text.
        """
        return cls.matches(content_type, "text/*")

    @classmethod
    def is_xml(cls, content_type: str) -> bool:
        """
        Check if a content type is XML.

        Args:
            content_type: The content type header value.

        Returns:
            True if the content type is XML.
        """
        return cls.matches(content_type, "application/xml") or cls.matches(content_type, "text/xml")

    @classmethod
    def get_extension(cls, content_type: str) -> str:
        """
        Get the file extension for a content type.

        Args:
            content_type: The content type header value.

        Returns:
            The file extension.
        """
        ext = mimetypes.guess_extension(content_type)
        if ext:
            return ext
        parsed = cls.parse(content_type)
        if parsed["type"] == "application" and parsed["subtype"] == "json":
            return ".json"
        if parsed["type"] == "text" and parsed["subtype"] == "html":
            return ".html"
        if parsed["type"] == "text" and parsed["subtype"] == "plain":
            return ".txt"
        return ""

    @classmethod
    def get_mime_type(cls, filename: str) -> str:
        """
        Get the MIME type for a filename.

        Args:
            filename: The filename.

        Returns:
            The MIME type.
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or cls.OCTET_STREAM

    @classmethod
    def get_encoding(cls, content_type: str) -> str:
        """
        Get the charset encoding from a content type.

        Args:
            content_type: The content type header value.

        Returns:
            The charset encoding or "utf-8" if not specified.
        """
        parsed = cls.parse(content_type)
        return parsed.get("parameters", {}).get("charset", "utf-8")


def ensure_json_content_type(request: Any) -> None:
    """
    Ensure the request has a JSON content type.

    Args:
        request: The request object.

    Raises:
        BadRequest: If the content type is not JSON.
    """
    content_type = request.headers.get("content-type", "")
    if not ContentType.is_json(content_type):
        raise BadRequest(f"Content-Type must be application/json, got: {content_type}")


def ensure_form_content_type(request: Any) -> None:
    """
    Ensure the request has a form content type.

    Args:
        request: The request object.

    Raises:
        BadRequest: If the content type is not form data.
    """
    content_type = request.headers.get("content-type", "")
    if not (ContentType.is_form(content_type) or ContentType.is_multipart(content_type)):
        raise BadRequest(
            "Content-Type must be application/x-www-form-urlencoded or multipart/form-data, "
            f"got: {content_type}"
        )


def get_accept_types(request: Any) -> list[dict[str, Any]]:
    """Parse the Accept header."""
    accept = request.headers.get("accept", "")
    if not accept:
        return []

    types: list[dict[str, Any]] = []
    for raw_part in accept.split(","):
        part = raw_part
        part = part.strip()
        if ";" in part:
            main, params = part.split(";", 1)
            weight = 1.0
            for param in params.split(";"):
                if param.strip().startswith("q="):
                    with contextlib.suppress(ValueError):
                        weight = float(param.strip().split("=")[1])
            types.append({"type": main.strip(), "q": weight})
        else:
            types.append({"type": part, "q": 1.0})

    return sorted(types, key=lambda x: x["q"], reverse=True)
