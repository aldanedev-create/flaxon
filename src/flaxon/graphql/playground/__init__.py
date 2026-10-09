from __future__ import annotations

from pathlib import Path

from flaxon.http import HTMLResponse, Request


class GraphiQLPlayground:
    def __init__(self, endpoint: str = "/graphql") -> None:
        self.endpoint = endpoint
        self._html = self._load_html()

    def _load_html(self) -> str:
        html_path = Path(__file__).parent / "graphiql.html"
        if html_path.exists():
            return html_path.read_text()
        return self._fallback_html()

    def _fallback_html(self) -> str:
        return """<!DOCTYPE html>
<html>
<head><title>GraphiQL</title></head>
<body>
    <h1>GraphiQL Playground</h1>
    <p>GraphQL endpoint: <strong>/graphql</strong></p>
    <p>Use a GraphQL client to explore the API.</p>
</body>
</html>"""

    async def render(self, request: Request) -> HTMLResponse:
        return HTMLResponse(self._html)


class AltairPlayground:
    def __init__(self, endpoint: str = "/graphql") -> None:
        self.endpoint = endpoint
        self._html = self._load_html()

    def _load_html(self) -> str:
        html_path = Path(__file__).parent / "altair.html"
        if html_path.exists():
            return html_path.read_text()
        return self._fallback_html()

    def _fallback_html(self) -> str:
        return """<!DOCTYPE html>
<html>
<head><title>Altair</title></head>
<body>
    <h1>Altair Playground</h1>
    <p>GraphQL endpoint: <strong>/graphql</strong></p>
</body>
</html>"""

    async def render(self, request: Request) -> HTMLResponse:
        return HTMLResponse(self._html)
