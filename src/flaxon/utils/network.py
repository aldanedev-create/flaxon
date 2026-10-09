from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urljoin, urlparse


def get_client_ip(scope: dict[str, Any]) -> str | None:
    """Get the client IP address from the scope."""
    client = scope.get("client")
    if client:
        return client[0]

    headers = scope.get("headers", [])
    for key, value in headers:
        if key.lower() == b"x-forwarded-for":
            return value.decode("latin-1").split(",")[0].strip()

    return None


def get_host(scope: dict[str, Any]) -> str | None:
    """Get the host from the scope."""
    headers = scope.get("headers", [])
    for key, value in headers:
        if key.lower() == b"host":
            return value.decode("latin-1")

    return None


def is_localhost(host: str) -> bool:
    """Check if a host is localhost."""
    return host in {"localhost", "127.0.0.1", "::1"}


def normalize_path(path: str) -> str:
    """Normalize a path by ensuring it starts with a slash and has no trailing slash."""
    if not path.startswith("/"):
        path = f"/{path}"
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    return path


def join_paths(base: str, *parts: str) -> str:
    """Join multiple path parts."""
    result = base
    for part in parts:
        result = urljoin(result, part)
    return normalize_path(result)


def parse_url(url: str) -> tuple[str, str, str, str]:
    """Parse a URL into scheme, host, path, and query."""
    parsed = urlparse(url)
    return parsed.scheme, parsed.netloc, parsed.path, parsed.query


def is_valid_ip(ip: str) -> bool:
    """Check if a string is a valid IP address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_host(host: str) -> bool:
    """Check if a string is a valid hostname."""
    pattern = (
        r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?"
        r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$"
    )
    return bool(re.match(pattern, host))
