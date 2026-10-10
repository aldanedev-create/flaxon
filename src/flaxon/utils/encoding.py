from __future__ import annotations

import base64
import urllib.parse
from typing import Any


def base64_encode(data: bytes | str) -> str:
    """Encode data to base64."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("utf-8")


def base64_decode(data: str | bytes) -> bytes:
    """Decode base64 data."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64decode(data)


def base64_url_encode(data: bytes | str) -> str:
    """Encode data to URL-safe base64."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("utf-8")


def base64_url_decode(data: str | bytes) -> bytes:
    """Decode URL-safe base64 data."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64decode(data)


def url_encode(data: dict[str, Any]) -> str:
    """Encode a dictionary as URL-encoded form data."""
    return urllib.parse.urlencode(data)


def url_decode(data: str) -> dict[str, Any]:
    """Decode URL-encoded form data to a dictionary."""
    return urllib.parse.parse_qs(data)


def json_escape(data: str) -> str:
    """Escape a string for use in JSON."""
    return (
        data
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def html_escape(data: str) -> str:
    """Escape a string for use in HTML."""
    return (
        data
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
