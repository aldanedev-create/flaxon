"""Serve the documentation assets (ReDoc, Swagger UI) that ship inside the package.

The files are vendored and pinned, so the interactive docs work offline and never depend on a
third-party CDN. See ``scripts/vendor_docs_assets.py`` for how they are updated and verified.
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path

from flaxon.http import Response

ASSETS_ROOT = Path(__file__).parent / "assets"
CACHE_CONTROL = "public, max-age=31536000, immutable"
JAVASCRIPT = "text/javascript; charset=utf-8"
STYLESHEET = "text/css; charset=utf-8"


@cache
def _load(package: str, name: str) -> tuple[bytes, str]:
    data = (ASSETS_ROOT / package / name).read_bytes()
    return data, f'"sha256-{hashlib.sha256(data).hexdigest()}"'


def asset_response(package: str, name: str, media_type: str, if_none_match: str | None = None) -> Response:
    """Serve a vendored file with long-lived caching, an ETag and ``304`` support."""
    body, etag = _load(package, name)
    headers = {"etag": etag, "cache-control": CACHE_CONTROL}
    if if_none_match:
        offered = {tag.strip().removeprefix("W/") for tag in if_none_match.split(",")}
        if etag in offered or "*" in offered:
            return Response(b"", status_code=304, headers=headers)
    return Response(body, headers=headers, media_type=media_type)
