"""Optional Teloce SPA integration for Flaxon applications."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from flaxon.http import HTMLResponse


@dataclass(frozen=True, slots=True)
class TeloceSource:
    """One application or module-owned Teloce source tree."""

    name: str
    directory: Path
    routes: dict[str, str] = field(default_factory=dict)


class Teloce:
    """Compile and serve one Teloce SPA from application and module sources."""

    def __init__(
        self,
        app: Any,
        *,
        ui_dir: str | Path = "ui",
        project_root: str | Path | None = None,
        build_dir: str | Path = ".flaxon/build",
        static_url: str = "/_flaxon",
        entry: str = "app.html",
        title: str | None = None,
        favicon: str | None = None,
        description: str | None = None,
        lang: str = "en",
        theme_color: str | None = None,
        stylesheets: list[str | dict[str, Any]] | None = None,
        scripts: list[str | dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.app = app
        self.project_root = Path(project_root or Path.cwd()).resolve()
        output = Path(build_dir)
        self.build_dir = (
            output.resolve() if output.is_absolute() else (self.project_root / output).resolve()
        )
        self.static_url = "/" + static_url.strip("/")
        self.entry = entry.replace("\\", "/").lstrip("/")
        self.title = title or app.name
        if not isinstance(lang, str) or not lang.strip():
            raise ValueError("lang must be a nonempty document language")
        self.lang = lang
        self.head_tags: list[str] = []
        if favicon is not None:
            self.head_tags.append(_resource_tag("link", {"rel": "icon", "href": favicon}))
        for name, value in (("description", description), ("theme-color", theme_color)):
            if value is not None:
                self.head_tags.append(f'<meta name="{name}" content="{html.escape(value, quote=True)}">')
        for resource in stylesheets or []:
            attributes = {"href": resource} if isinstance(resource, str) else dict(resource)
            self.head_tags.append(_resource_tag("link", {"rel": "stylesheet", **attributes}))
        for resource in scripts or []:
            attributes = {"src": resource} if isinstance(resource, str) else dict(resource)
            self.head_tags.append(_resource_tag("script", attributes))
        self.options = dict(options or {})
        self.sources: list[TeloceSource] = []
        self.build_result: dict[str, Any] | None = None
        self.router_output: str | None = None
        self._building = False

        self.register_source("app", ui_dir)
        for source in getattr(app, "_teloce_ui_sources", []):
            self.register_source(source.name, source.directory, routes=source.routes)

        cache_control = (
            "no-cache"
        )
        app.mount_static(self.static_url, str(self.build_dir), cache_control=cache_control)
        app.on_startup(self.build)

    def register_source(
        self,
        name: str,
        directory: str | Path,
        *,
        routes: dict[str, str] | None = None,
    ) -> None:
        """Register a UI root contributed by the app or a mounted module."""
        source_path = Path(directory)
        if not source_path.is_absolute():
            source_path = self.project_root / source_path
        source_path = source_path.resolve()
        try:
            source_path.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("Teloce UI directories must stay inside project_root") from exc
        if any(source.name == name for source in self.sources):
            raise ValueError(f"Teloce UI source {name!r} is already registered")
        if any(source.directory == source_path for source in self.sources):
            raise ValueError(f"Teloce UI directory is already registered: {source_path}")
        self.sources.append(TeloceSource(name, source_path, dict(routes or {})))
        self.build_result = None

    def build(self) -> dict[str, Any]:
        """Build all registered sources and one shared client-side router."""
        if self._building:
            raise RuntimeError("A Teloce build is already running")
        self._building = True
        try:
            try:
                from teloce.build import Builder
                from teloce.router import generate_spa_router
            except ImportError as exc:
                raise RuntimeError(
                    "Teloce support requires the optional dependency: "
                    "pip install --upgrade flaxon teloce-py"
                ) from exc

            missing = [str(source.directory) for source in self.sources if not source.directory.is_dir()]
            if missing:
                raise RuntimeError(f"Teloce UI directory does not exist: {missing[0]}")

            source_roots = [
                source.directory.relative_to(self.project_root).as_posix()
                for source in self.sources
            ]
            build_options = {
                "mode": "development" if self.app.debug else "production",
                "production": not self.app.debug,
                "dev": self.app.debug,
                "clean": True,
                "html_mode": True,
                "source_roots": source_roots,
                "source_maps": self.app.debug,
                "hash_assets": not self.app.debug,
                "extract_css": not self.app.debug,
                "spa": False,
                **self.options,
            }
            result = Builder(build_options).build(self.project_root, self.build_dir)
            if result.get("failed"):
                details = "; ".join(
                    f"{item.get('file')}: {item.get('error')}"
                    for item in result.get("errors", [])
                )
                raise RuntimeError(f"Teloce build failed: {details}")

            page_dirs: list[Path] = []
            route_overrides: dict[str, str] = {}
            for source in self.sources:
                relative_root = source.directory.relative_to(self.project_root)
                pages = self.build_dir / relative_root / "pages"
                if pages.is_dir() and any(pages.rglob("*.js")):
                    page_dirs.append(pages)
                    for filename, route in source.routes.items():
                        normalized_filename = filename.replace("\\", "/")
                        route_overrides[
                            f"{pages.as_posix()}::{normalized_filename}"
                        ] = route

            self.router_output = None
            if page_dirs:
                router_path = self.build_dir / "router.js"
                generate_spa_router(
                    router_path,
                    page_dirs,
                    mode=self.options.get("spa_mode", "history"),
                    base=self.options.get("spa_base", "/"),
                    route_overrides=route_overrides,
                    minify=False,
                )
                if not self.app.debug and self.options.get("minify", True):
                    from minifyjs import minify
                    optimized = minify(router_path.read_text(encoding="utf-8"),
                                       compress=True, mangle=True, format="esm",
                                       target=self.options.get("target") or "es2020",
                                       source_name="router.js")
                    router_path.write_text(optimized.code, encoding="utf-8")
                self.router_output = router_path.relative_to(self.build_dir).as_posix()

            self._assert_entry_exists(self.entry)
            self.build_result = result
            return result
        finally:
            self._building = False

    def render(
        self,
        entry: str | None = None,
        context: dict[str, Any] | None = None,
        *,
        title: str | None = None,
    ) -> HTMLResponse:
        """Return the compiled SPA shell, building lazily outside lifespan tests."""
        if self.build_result is None:
            self.build()
        selected_entry = (entry or self.entry).replace("\\", "/").lstrip("/")
        output = self._entry_output(selected_entry)
        self._assert_entry_exists(selected_entry)
        payload = json.dumps(context or {}, ensure_ascii=False, default=str)
        payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        app_url = f"{self.static_url}/{output}"
        router_import = ""
        router_mount = ""
        if self.router_output:
            router_url = f"{self.static_url}/{self.router_output}"
            router_import = f'import router from {json.dumps(router_url)};'
            router_mount = (
                'const view = document.querySelector("[data-teloce-router-view], #router-view");'
                "if (view) router.mount(view, context);"
                "window.__TELOCE_ROUTER__ = router;"
                "document.addEventListener('click', event => {"
                "const link = event.target.closest?.('a[data-teloce-link]');"
                "if (!link || link.hasAttribute('download') || (link.target && link.target.toLowerCase() !== '_self') || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;"
                "const url = new URL(link.href, location.href);"
                "if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) return;"
                "if (url.pathname === location.pathname && url.search === location.search && url.hash) return;"
                "if (!router.resolve(url.pathname + url.search)) return;"
                "event.preventDefault(); router.push(url.pathname + url.search + url.hash);"
                "});"
            )
        aggregate_styles = sorted(self.build_dir.glob("styles*.css"))
        style_files = aggregate_styles or sorted(self.build_dir.rglob("*.css"))
        css_links = [
            f'<link rel="stylesheet" href="{self.static_url}/{path.relative_to(self.build_dir).as_posix()}">'
            for path in style_files
        ]
        css_link = "\n  ".join(css_links)
        head_tags = "\n  ".join(self.head_tags)
        document = f"""<!doctype html>
<html lang="{html.escape(self.lang, quote=True)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title or self.title)}</title>
  {css_link}
  {head_tags}
</head>
<body>
  <div id="app"></div>
  <script id="__FLAXON_TELOCE_DATA__" type="application/json">{payload}</script>
  <script type="module">
    import {{ mount }} from {json.dumps(app_url)};
    {router_import}
    const context = JSON.parse(document.getElementById("__FLAXON_TELOCE_DATA__").textContent);
    window.__FLAXON_TELOCE__ = mount("#app", context);
    {router_mount}
  </script>
</body>
</html>"""
        return HTMLResponse(
            document,
            headers={"cache-control": "no-store" if self.app.debug else "no-cache"},
        )

    def _entry_output(self, entry: str) -> str:
        source = self._resolve_entry(entry)
        relative = source.relative_to(self.project_root)
        return relative.with_suffix(".js").as_posix()

    def _assert_entry_exists(self, entry: str) -> None:
        output = self.build_dir / self._entry_output(entry)
        if not output.is_file():
            raise RuntimeError(f"Compiled Teloce entry does not exist: {output}")

    def _resolve_entry(self, entry: str) -> Path:
        candidates = []
        for source in self.sources:
            candidate = (source.directory / entry).resolve()
            try:
                candidate.relative_to(source.directory)
            except ValueError:
                continue
            candidates.append(candidate)
        match = next((candidate for candidate in candidates if candidate.is_file()), None)
        if match is None:
            raise RuntimeError(f"Teloce entry was not found in a registered UI source: {entry}")
        return match


def install_teloce(
    app: Any,
    **options: Any,
) -> Teloce:
    """Install one Teloce integration on an application."""
    existing = getattr(app, "teloce", None)
    if existing is not None:
        raise RuntimeError("Teloce is already configured for this application")
    integration = Teloce(app, **options)
    app.teloce = integration
    return integration


def _resource_tag(tag: str, attributes: dict[str, Any]) -> str:
    """Render explicitly supported resource attributes without accepting raw HTML."""
    allowed = {"src", "type", "defer", "async", "integrity", "crossorigin", "referrerpolicy"} if tag == "script" else {"href", "rel", "type", "media", "integrity", "crossorigin", "referrerpolicy", "sizes"}
    unknown = attributes.keys() - allowed
    if unknown:
        raise ValueError(f"Unsupported {tag} attributes: {', '.join(sorted(unknown))}")
    key = "src" if tag == "script" else "href"
    url = attributes.get(key)
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"{tag} requires a nonempty {key}")
    if any(ord(char) < 32 for char in url) or "\\" in url:
        raise ValueError("Resource URLs must not contain control characters or backslashes")
    if urlsplit(url).scheme.lower() not in {"", "http", "https"}:
        raise ValueError("Resource URLs must be relative, HTTP or HTTPS")
    parts = []
    for name, value in attributes.items():
        if name in {"defer", "async"}:
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be a boolean")
            if value:
                parts.append(name)
        elif value is not None:
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            parts.append(f'{name}="{html.escape(value, quote=True)}"')
    opening = f"<{tag} {' '.join(parts)}>"
    return opening + ("</script>" if tag == "script" else "")
