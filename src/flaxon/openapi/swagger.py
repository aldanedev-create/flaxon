from __future__ import annotations

import html
import json

from flaxon.http import HTMLResponse, Response

from .assets import ASSETS_ROOT, JAVASCRIPT, STYLESHEET, asset_response

#: The vendored Swagger UI release. Update it with ``python scripts/vendor_docs_assets.py swagger-ui``.
SWAGGER_UI_VERSION = "5.35.0"
ASSET_DIR = ASSETS_ROOT / "swagger_ui"
SWAGGER_ASSETS = {
    "swagger-ui.css": STYLESHEET,
    "swagger-ui-bundle.js": JAVASCRIPT,
}


def swagger_asset_base(docs_url: str = "/docs") -> str:
    """Base URL the bundled Swagger UI files are served from, next to the docs page.

    The version is part of the path, so the files can be cached forever and a new release
    is fetched automatically.
    """
    return f"{docs_url.rstrip('/')}/assets/{SWAGGER_UI_VERSION}"


def swagger_asset_response(name: str, if_none_match: str | None = None) -> Response:
    """Serve one vendored Swagger UI file with long-lived caching and an ETag."""
    return asset_response("swagger_ui", name, SWAGGER_ASSETS[name], if_none_match)


class SwaggerUI:
    """Render a Swagger UI shell for an OpenAPI endpoint.

    By default the page loads the Swagger UI files that ship with Flaxon, so it works offline and
    does not depend on a third-party CDN. Pass ``asset_url`` (a base URL serving ``swagger-ui.css``
    and ``swagger-ui-bundle.js``) to host them yourself.
    """

    def __init__(
        self,
        openapi_url: str = "/openapi.json",
        title: str = "Flaxon API",
        *,
        asset_url: str | None = None,
        persist_authorization: bool = False,
        try_it_out_enabled: bool = True,
    ) -> None:
        self.openapi_url = openapi_url
        self.title = title
        self.asset_url = (asset_url or swagger_asset_base()).rstrip("/")
        self.persist_authorization = persist_authorization
        self.try_it_out_enabled = try_it_out_enabled

    def render(self) -> HTMLResponse:
        """Render the requested content using the supplied context."""
        title = html.escape(self.title, quote=True)
        asset_url = html.escape(self.asset_url, quote=True)
        config = json.dumps({
            "url": self.openapi_url,
            "dom_id": "#swagger-ui",
            "deepLinking": True,
            "docExpansion": "list",
            "defaultModelsExpandDepth": 1,
            "defaultModelExpandDepth": 1,
            "displayRequestDuration": True,
            "filter": True,
            "persistAuthorization": self.persist_authorization,
            "tryItOutEnabled": self.try_it_out_enabled,
            "showExtensions": True,
            "showCommonExtensions": True,
            # Swagger UI's built-in default points its online validator at validator.swagger.io, a
            # third-party service. Turn it off so the page never contacts one.
            "validatorUrl": None,
        }).replace("</", "<\\/")
        html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} - Swagger UI</title>
    <link rel="stylesheet" href="{asset_url}/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="{asset_url}/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            window.ui = SwaggerUIBundle({config});
        }};
    </script>
</body>
</html>"""
        return HTMLResponse(html_text)


def create_swagger_ui(openapi_url: str = "/openapi.json", title: str = "Flaxon API") -> HTMLResponse:
    """Create the swagger ui."""
    return SwaggerUI(openapi_url, title).render()
