from __future__ import annotations

import html

from flaxon.http import HTMLResponse, Response

from .assets import ASSETS_ROOT, JAVASCRIPT, asset_response

#: The vendored ReDoc release. Update it with ``python scripts/vendor_docs_assets.py redoc --version X.Y.Z``.
REDOC_VERSION = "2.5.4"
BUNDLE_NAME = "redoc.standalone.js"
ASSET_DIR = ASSETS_ROOT / "redoc"


def redoc_asset_path(redoc_url: str = "/redoc") -> str:
    """Path the bundled ReDoc script is served from: next to the ReDoc page itself."""
    return f"{redoc_url.rstrip('/')}/{BUNDLE_NAME}"


def redoc_asset_url(redoc_url: str = "/redoc") -> str:
    """URL for the bundled script. The version query string busts caches on upgrade."""
    return f"{redoc_asset_path(redoc_url)}?v={REDOC_VERSION}"


def redoc_asset_response(if_none_match: str | None = None) -> Response:
    """Serve the vendored ReDoc bundle with long-lived caching and an ETag."""
    return asset_response("redoc", BUNDLE_NAME, JAVASCRIPT, if_none_match)


class ReDoc:
    """Render a ReDoc shell for an OpenAPI endpoint.

    By default the page loads the ReDoc bundle that ships with Flaxon, so it works offline and
    does not depend on a third-party CDN. Pass ``asset_url`` to use a bundle you host yourself.
    """

    def __init__(
        self,
        openapi_url: str = "/openapi.json",
        title: str = "Flaxon API",
        *,
        asset_url: str | None = None,
    ) -> None:
        self.openapi_url = openapi_url
        self.title = title
        self.asset_url = asset_url or redoc_asset_url()

    def render(self) -> HTMLResponse:
        """Render the requested content using the supplied context."""
        title = html.escape(self.title, quote=True)
        openapi_url = html.escape(self.openapi_url, quote=True)
        asset_url = html.escape(self.asset_url, quote=True)
        html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} - ReDoc</title>
    <style>body {{ margin: 0; }} redoc {{ display: block; }}</style>
</head>
<body>
    <redoc spec-url="{openapi_url}"></redoc>
    <script src="{asset_url}"></script>
</body>
</html>"""
        return HTMLResponse(html_text)


def create_redoc(openapi_url: str = "/openapi.json", title: str = "Flaxon API") -> HTMLResponse:
    """Create the redoc."""
    return ReDoc(openapi_url, title).render()
