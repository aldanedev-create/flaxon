from __future__ import annotations

import html
import json

from flaxon.http import HTMLResponse


class SwaggerUI:
    """Render a self-contained Swagger UI shell for an OpenAPI endpoint."""

    def __init__(
        self,
        openapi_url: str = "/openapi.json",
        title: str = "Flaxon API",
        *,
        asset_url: str = "https://unpkg.com/swagger-ui-dist@5",
        persist_authorization: bool = False,
        try_it_out_enabled: bool = True,
    ) -> None:
        self.openapi_url = openapi_url
        self.title = title
        self.asset_url = asset_url.rstrip("/")
        self.persist_authorization = persist_authorization
        self.try_it_out_enabled = try_it_out_enabled

    def render(self) -> HTMLResponse:
        title = html.escape(self.title, quote=True)
        asset_url = html.escape(self.asset_url, quote=True)
        config = json.dumps(
            {
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
            }
        ).replace("</", "<\\/")
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
    return SwaggerUI(openapi_url, title).render()
