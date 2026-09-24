from __future__ import annotations

import html

from flaxon.http import HTMLResponse


class ReDoc:
    """Render a ReDoc shell for an OpenAPI endpoint."""

    def __init__(
        self,
        openapi_url: str = "/openapi.json",
        title: str = "Flaxon API",
        *,
        asset_url: str = "https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js",
    ) -> None:
        self.openapi_url = openapi_url
        self.title = title
        self.asset_url = asset_url

    def render(self) -> HTMLResponse:
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
    return ReDoc(openapi_url, title).render()
