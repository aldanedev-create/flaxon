"""Teloce-powered extension points for the Flaxon admin.

An *admin extension* is an installed package that contributes custom fields,
dashboard cards, tools and pages written as Teloce ``.vel`` components. Teloce
is a Python compiler, so authors write Python and TypeScript and never need
Node.js, npm or a CDN at build or run time.

Convention
----------
A package named ``flaxon-admin-<something>`` exposes an entry point in the
``flaxon.admin`` group::

    [project.entry-points."flaxon.admin"]
    rating = "flaxon_admin_rating:RatingExtension"

The entry point resolves to an :class:`AdminExtension` subclass (or instance).
Only distributions whose name starts with ``flaxon-admin-`` are auto-discovered;
anything else in the group is ignored with a warning, so an unrelated package
cannot silently attach code to the admin. Discovery can be disabled with
``AdminConfig(enable_extensions=False)`` or narrowed with
``AdminConfig(disabled_extensions=(...))``; explicit instances can be passed in
``AdminConfig(extensions=[...])``.

Components are compiled once at startup by ``teloce-py`` and served as ES
modules from ``<admin>/extensions/assets/<name>.js``. Every mount point is also
rendered on the server, so a page still shows the stored value when JavaScript
is unavailable. Extension code is trusted, installed Python; it is not a
sandbox. Everything an extension renders is escaped, and page handlers keep the
same permission and CSRF checks as the rest of the admin.
"""

from __future__ import annotations

import html
import inspect
import json
import logging
import re
from collections.abc import Iterable
from importlib import metadata
from pathlib import Path
from typing import Any, ClassVar

from .metrics import Metric
from .resources import Field

logger = logging.getLogger("flaxon.admin.extensions")

ADMIN_EXTENSION_GROUP = "flaxon.admin"
EXTENSION_DISTRIBUTION_PREFIX = "flaxon-admin-"
_COMPONENT_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_EXTENSION_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")

__all__ = [
    "ADMIN_EXTENSION_GROUP",
    "EXTENSION_DISTRIBUTION_PREFIX",
    "AdminExtension",
    "Component",
    "ExtensionError",
    "ExtensionPage",
    "ExtensionRegistry",
    "TeloceCard",
    "TeloceField",
    "Tool",
    "load_extensions",
]


class ExtensionError(RuntimeError):
    """Raised when an admin extension cannot be loaded or compiled."""


def _teloce_module() -> Any:
    """Import ``teloce`` lazily so Flaxon stays usable without the extra."""
    try:
        import teloce  # type: ignore[import-untyped]  # noqa: PLC0415 - optional dependency
    except ImportError as exc:  # pragma: no cover - exercised by an isolated test
        raise ExtensionError(
            "Admin Teloce components require teloce-py: pip install 'flaxon[teloce]'"
        ) from exc
    return teloce


def _jsonable(value: Any) -> Any:
    """Return a JSON-serialisable copy of ``value`` for component props."""
    return json.loads(json.dumps(value, ensure_ascii=True, default=str))


class Component:
    """One ``.vel`` single-file component owned by an extension.

    ``source`` is either a :class:`~pathlib.Path` to the file or the component
    source itself. Compilation is lazy, cached, and performed by the same
    Teloce compiler the rest of Flaxon uses.
    """

    def __init__(self, name: str, source: str | Path) -> None:
        if not _COMPONENT_NAME.match(name):
            raise ValueError("Component names must match ^[a-z][a-z0-9-]*$")
        self.name = name
        if isinstance(source, Path):
            self.path: Path | None = source
            self._text: str | None = None
        else:
            self.path = None
            self._text = str(source)
        self._code: str | None = None

    @property
    def text(self) -> str:
        """Return the component source, reading it from disk when needed."""
        if self._text is None:
            if self.path is None:  # pragma: no cover - constructor guarantees one
                raise ExtensionError(f"Component {self.name!r} has no source")
            try:
                self._text = self.path.read_text(encoding="utf-8")
            except OSError as exc:
                raise ExtensionError(f"Cannot read component {self.name!r}: {exc}") from exc
        return self._text

    def compile(self) -> str:
        """Compile the component to a JavaScript ES module (cached)."""
        if self._code is not None:
            return self._code
        teloce = _teloce_module()
        try:
            result = teloce.compile(self.text, filename=f"{self.name}.vel")
        except Exception as exc:
            raise ExtensionError(f"Component {self.name!r} failed to compile: {exc}") from exc
        if not result.get("success", True):
            errors = result.get("diagnostics", {}).get("errors") or result.get("errors") or []
            message = "; ".join(
                str(item.get("message", item)) if isinstance(item, dict) else str(item) for item in errors
            )
            raise ExtensionError(f"Component {self.name!r} failed to compile: {message or 'unknown error'}")
        code = result.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ExtensionError(f"Component {self.name!r} produced no JavaScript")
        self._code = code
        return code

    async def render(self, props: dict[str, Any] | None = None) -> str:
        """Render the component to HTML on the server (no browser script runs)."""
        teloce = _teloce_module()
        try:
            rendered = await teloce.render_static_component(self.text, _jsonable(props or {}))
            return str(rendered)
        except Exception as exc:
            raise ExtensionError(f"Component {self.name!r} failed to render: {exc}") from exc

    def mount_point(self, props: dict[str, Any] | None = None, *, value: Any = None, body: str = "") -> str:
        """Return the escaped mount element the browser bundle enhances."""
        payload = html.escape(json.dumps(_jsonable(props or {}), ensure_ascii=True), quote=True)
        attributes = f' data-teloce-component="{self.name}" data-teloce-props="{payload}"'
        if value is not None:
            attributes += f' data-teloce-value="{html.escape(str(value), quote=True)}"'
        return f'<div class="fx-teloce"{attributes}>{body}</div>'

    def __repr__(self) -> str:
        return f"Component(name={self.name!r})"


class AdminExtension:
    """Base class for a ``flaxon-admin-*`` package.

    Subclasses set :attr:`name` and :attr:`label`, optionally override
    :meth:`setup`, and return their contributions from :meth:`fields`,
    :meth:`cards`, :meth:`pages` and :meth:`tools`. Components live in
    ``<package>/ui/*.vel`` and are referenced with :meth:`component`.
    """

    name: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""
    version: ClassVar[str] = "0.1.0"
    ui_dir: ClassVar[str] = "ui"

    def __init__(self, *, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else self._default_root()
        self.dashboard: Any = None
        self._components: dict[str, Component] = {}

    @classmethod
    def _default_root(cls) -> Path:
        # Classes created with exec() have no source file; component() still
        # fails clearly when the referenced .vel file does not exist.
        try:
            return Path(inspect.getfile(cls)).resolve().parent
        except (TypeError, OSError):
            return Path.cwd()

    # -- lifecycle -----------------------------------------------------------
    def bind(self, dashboard: Any) -> None:
        """Attach the extension to a dashboard (called once by the registry)."""
        if self.dashboard is not None and self.dashboard is not dashboard:
            raise ExtensionError(f"Extension {self.name!r} is already bound to another dashboard")
        if not _EXTENSION_NAME.match(self.name or ""):
            raise ExtensionError("AdminExtension.name must match ^[a-z][a-z0-9_-]*$")
        self.dashboard = dashboard

    def setup(self, dashboard: Any) -> None:
        """Optional hook for permissions or other registration work."""

    def model_registered(self, dashboard: Any, admin_model: Any) -> None:
        """Called when a model is registered after the extension was loaded.

        Extensions that contribute per-model cards or pages use this instead of
        assuming models exist when the dashboard is constructed.
        """

    # -- contributions -------------------------------------------------------
    def fields(self) -> list[type[Field]]:
        """Return custom field classes contributed by this extension."""
        return []

    def cards(self) -> list[Metric]:
        """Return dashboard cards contributed by this extension."""
        return []

    def pages(self) -> list[ExtensionPage]:
        """Return custom admin pages contributed by this extension."""
        return []

    def tools(self) -> list[Tool]:
        """Return tools shown on the admin dashboard."""
        return []

    # -- components ----------------------------------------------------------
    def component(self, filename: str) -> Component:
        """Return (and cache) the component stored in ``ui/<filename>``."""
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise ExtensionError("Component filenames must stay inside the ui directory")
        path = (self.root / self.ui_dir / relative).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ExtensionError("Component filenames must stay inside the extension") from exc
        if not path.is_file():
            raise ExtensionError(f"Component file does not exist: {path}")
        name = path.stem
        existing = self._components.get(name)
        if existing is not None:
            if existing.path != path:
                raise ExtensionError(f"Component name {name!r} is used by two files")
            return existing
        component = Component(name, path)
        self._components[name] = component
        return component

    def components(self) -> list[Component]:
        """Return every component in ``ui/`` plus any declared out of tree."""
        directory = self.root / self.ui_dir
        if directory.is_dir():
            for path in sorted(directory.glob("*.vel")):
                self.component(path.name)
        return sorted(self._components.values(), key=lambda item: item.name)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, version={self.version!r})"


class ExtensionPage:
    """A custom admin page rendered from a Teloce component.

    The page keeps the admin's session, permission and CSRF rules: it is mounted
    through :meth:`~flaxon.admin.dashboard.AdminDashboard.add_view`, and the
    handler only accepts GET/HEAD unless ``methods`` adds more.
    """

    def __init__(
        self,
        name: str,
        component: Component,
        *,
        label: str | None = None,
        url: str | None = None,
        permission: str = "admin.view_dashboard",
        icon: str = "fa-puzzle-piece",
        category: str = "Extensions",
        description: str = "",
        props: Any = None,
        methods: set[str] | None = None,
    ) -> None:
        self.name = name
        self.component = component
        self.label = label or name.replace("-", " ").title()
        self.url = url or name.lower().replace(" ", "-")
        self.permission = permission
        self.icon = icon
        self.category = category
        self.description = description
        self.props = props
        self.methods = methods or {"GET"}

    async def build_props(self, request: Any) -> dict[str, Any]:
        """Evaluate the page's props for ``request`` (sync or async callables)."""
        if self.props is None:
            return {}
        value = self.props(request)
        if hasattr(value, "__await__"):
            value = await value
        if not isinstance(value, dict):
            raise ExtensionError(f"Page {self.name!r} props must return a dictionary")
        return value

    async def handler(self, request: Any) -> Any:
        """Render the page through the dashboard's Jinax environment."""
        dashboard = self._dashboard
        props = await self.build_props(request)
        body = await self.component.render(props)
        context = {
            "title": self.label,
            "page": self,
            "component": self.component.name,
            "component_body": body,
            "component_props": json.dumps(_jsonable(props), ensure_ascii=True),
            "user": getattr(request, "user", None),
            "models": dashboard.registry.get_all(),
            "custom_views": dashboard.custom_views,
        }
        return await dashboard.jinax.render_response("admin/extension_page.html", context)

    def bind(self, dashboard: Any) -> None:
        """Remember the dashboard used by :meth:`handler`."""
        self._dashboard = dashboard


class Tool:
    """A dashboard shortcut contributed by an extension.

    A tool is a labelled link to an :class:`ExtensionPage`; it deliberately does
    no work on the dashboard itself, so adding tools cannot slow the index down.
    """

    def __init__(
        self,
        label: str,
        page: ExtensionPage,
        *,
        icon: str = "fa-toolbox",
        description: str = "",
        permission: str | None = None,
    ) -> None:
        self.label = label
        self.page = page
        self.icon = icon
        self.description = description or page.description
        self.permission = permission or page.permission

    @property
    def url(self) -> str:
        """Return the page URL, relative to the admin prefix."""
        return self.page.url


class TeloceField(Field):
    """A form field whose control is a Teloce component.

    The component receives ``name``, ``label`` and ``required`` props plus any
    extra props declared here, and the current value as ``value``. It must
    render a real form control carrying the ``name`` prop so the form submits
    once the component mounts.

    Until the browser bundle runs, a plain HTML control (``fallback``: ``text``,
    ``number`` or ``select``) keeps the form usable, including without
    JavaScript. Teloce's static renderer interpolates text and repeats ``v-for``
    blocks but does not evaluate dynamic attribute bindings, so the fallback is
    what makes the no-JavaScript path honest. Server-side validation stays in
    Python: override :meth:`~flaxon.admin.resources.Field.validation_field` or
    pass ``rules``.
    """

    kind = "teloce"

    def __init__(
        self,
        name: str,
        component: Component,
        *,
        props: dict[str, Any] | None = None,
        fallback: str = "text",
        fallback_choices: Iterable[tuple[Any, str]] = (),
        **options: Any,
    ) -> None:
        super().__init__(name, **options)
        if fallback not in {"text", "number", "select"}:
            raise ValueError("fallback must be 'text', 'number' or 'select'")
        self.component = component
        self.extra_props = dict(props or {})
        self.fallback = fallback
        self.fallback_choices = list(fallback_choices)
        self.widget = "admin/extensions/field.html"

    def props_for(self, value: Any = None) -> dict[str, Any]:
        """Return the props passed to the component for ``value``."""
        props = {
            "name": self.name,
            "label": self.label,
            "required": self.required,
            **self.extra_props,
        }
        if value is not None:
            props["value"] = value
        return props

    def schema_entry(self) -> dict[str, Any]:
        """Expose the component and its static props to the field template."""
        entry = super().schema_entry()
        entry["kind"] = self.kind
        entry["widget"] = self.widget
        entry["component"] = self.component.name
        entry["component_props"] = json.dumps(self.props_for(), ensure_ascii=True, default=str)
        entry["fallback"] = self.fallback
        entry["fallback_choices"] = [[str(value), label] for value, label in self.fallback_choices]
        return entry


class TeloceCard(Metric):
    """A dashboard card whose markup is a Teloce component.

    The data is computed in Python (typically SQL through the ORM) and passed to
    the component as props; the component only renders. ``calculate`` may be a
    sync or async callable and receives the request.
    """

    kind = "teloce"

    def __init__(
        self,
        title: str,
        component: Component,
        *,
        calculate: Any,
        props: Any = None,
        **options: Any,
    ) -> None:
        super().__init__(title, **options)
        self.component = component
        self._calculate = calculate
        self._props = props

    async def calculate(self, request: Any = None, *, now: Any = None) -> dict[str, Any]:
        """Return the card data, awaiting the callable when needed."""
        value = self._calculate(request)
        if hasattr(value, "__await__"):
            value = await value
        if not isinstance(value, dict):
            raise ExtensionError(f"Card {self.title!r} calculate() must return a dictionary")
        return value

    async def render(self, data: dict[str, Any]) -> str:  # type: ignore[override]
        """Render the component on the server and return its mount point."""
        props = {"title": self.title, "description": self.description, "data": data}
        if self._props is not None:
            extra = self._props(data)
            if hasattr(extra, "__await__"):
                extra = await extra
            if not isinstance(extra, dict):
                raise ExtensionError(f"Card {self.title!r} props must return a dictionary")
            props.update(extra)
        body = await self.component.render(props)
        return self.component.mount_point(
            {"title": self.title, "description": self.description, "data": data},
            body=body,
        )


class ExtensionRegistry:
    """Owns extension discovery, validation, compilation and asset serving."""

    def __init__(self, dashboard: Any) -> None:
        self.dashboard = dashboard
        self.extensions: list[AdminExtension] = []
        self.field_types: dict[str, type[Field]] = {}
        self.pages: list[ExtensionPage] = []
        self.tools: list[Tool] = []
        self._components: dict[str, Component] = {}
        self._bundled = False

    # -- registration --------------------------------------------------------
    def register(self, extension: AdminExtension) -> AdminExtension:
        """Bind and register one extension; contributions are added immediately."""
        if not isinstance(extension, AdminExtension):
            raise TypeError("Admin extensions must subclass AdminExtension")
        if any(item.name == extension.name for item in self.extensions):
            raise ExtensionError(f"Admin extension {extension.name!r} is already registered")
        extension.bind(self.dashboard)
        extension.setup(self.dashboard)
        for field_type in extension.fields():
            if not issubclass(field_type, Field):
                raise TypeError(f"{extension.name}: fields() must return Field subclasses")
            self.field_types[field_type.kind] = field_type
        for card in extension.cards():
            self.dashboard.register_metric(card)
        for page in extension.pages():
            page.bind(self.dashboard)
            self.dashboard.add_view(
                page.handler,
                page.label,
                url=page.url,
                category=page.category,
                icon=page.icon,
                methods=page.methods,
                permission=page.permission,
            )
            self.pages.append(page)
        for tool in extension.tools():
            tool.page.bind(self.dashboard)
            self.tools.append(tool)
        for component in extension.components():
            existing = self._components.get(component.name)
            if existing is not None and existing.path != component.path:
                raise ExtensionError(f"Component name {component.name!r} is contributed twice")
            self._components[component.name] = component
        self.extensions.append(extension)
        logger.info("Registered admin extension %s %s", extension.name, extension.version)
        return extension

    def load(self, *, include: Iterable[AdminExtension] | None = None) -> list[AdminExtension]:
        """Discover ``flaxon-admin-*`` entry points and register the results."""
        for extension in load_extensions(
            disabled=getattr(self.dashboard.config, "disabled_extensions", ()),
        ):
            self.register(extension)
        for extension in include or ():
            # An extension may be both installed (discovered above) and listed
            # explicitly in config. Registering it twice would raise, so treat
            # an include whose name is already present as a no-op.
            if any(item.name == extension.name for item in self.extensions):
                continue
            self.register(extension)
        return list(self.extensions)

    # -- assets --------------------------------------------------------------
    @property
    def component_names(self) -> list[str]:
        """Return the names of every registered component."""
        return sorted(self._components)

    def component(self, name: str) -> Component:
        """Return a registered component by name."""
        try:
            return self._components[name]
        except KeyError as exc:
            raise ExtensionError(f"Unknown admin component: {name!r}") from exc

    def code(self, name: str) -> str:
        """Return the compiled JavaScript for a component."""
        return self.component(name).compile()

    def build(self) -> None:
        """Compile every component once; fail early on a broken extension."""
        for name in self.component_names:
            self._components[name].compile()
        self._bundled = True

    def bundle(self) -> str:
        """Return the ES module that mounts every component on the page."""
        if not self._bundled:
            self.build()
        imports = []
        entries = []
        for index, name in enumerate(self.component_names):
            alias = f"component{index}"
            imports.append(f'import * as {alias} from "./assets/{name}.js";')
            entries.append(f"  {json.dumps(name)}: {alias},")
        registry = "\n".join(entries)
        return (
            "// Generated by flaxon.admin.extensions - do not edit.\n"
            + "\n".join(imports)
            + "\n\nconst registry = {\n"
            + registry
            + "\n};\n\n"
            + _MOUNT_SCRIPT
        )

    @property
    def bundle_url(self) -> str:
        """Return the admin-relative URL of the extension bundle, if any."""
        if not self.component_names:
            return ""
        return f"{self.dashboard.url_prefix}/extensions/bundle.js"

    def asset_url(self, name: str) -> str:
        """Return the admin-relative URL of one compiled component."""
        return f"{self.dashboard.url_prefix}/extensions/assets/{name}.js"


_MOUNT_SCRIPT = """
function mountAll(root) {
  root.querySelectorAll("[data-teloce-component]").forEach(function (element) {
    const name = element.getAttribute("data-teloce-component");
    const factory = registry[name];
    if (!factory || element.dataset.teloceMounted === "1") return;
    let props = {};
    try {
      props = JSON.parse(element.getAttribute("data-teloce-props") || "{}");
    } catch (error) {
      console.error("Invalid Teloce props for " + name, error);
      return;
    }
    if (element.hasAttribute("data-teloce-value")) {
      const raw = element.getAttribute("data-teloce-value");
      props.value = raw !== "" && !Number.isNaN(Number(raw)) ? Number(raw) : raw;
    }
    element.dataset.teloceMounted = "1";
    try {
      factory.mount(element, props);
    } catch (error) {
      console.error("Teloce component failed to mount: " + name, error);
    }
  });
}

mountAll(document);
document.addEventListener("teloce:mount", function (event) {
  mountAll(event.target instanceof Element ? event.target : document);
});
"""


def load_extensions(
    *,
    group: str = ADMIN_EXTENSION_GROUP,
    disabled: Iterable[str] = (),
    entry_points: Any = None,
) -> list[AdminExtension]:
    """Load extensions from installed ``flaxon-admin-*`` distributions.

    Only entry points belonging to a distribution named ``flaxon-admin-*`` are
    loaded. Others in the group are skipped with a warning instead of failing
    the application, and a broken extension raises :class:`ExtensionError` with
    the entry point name so the cause is obvious.
    """
    blocked = {str(item).lower().replace("_", "-") for item in disabled}
    discovered = entry_points if entry_points is not None else metadata.entry_points(group=group)
    extensions: list[AdminExtension] = []
    for entry_point in discovered:
        distribution = getattr(entry_point, "dist", None)
        distribution_name = getattr(distribution, "name", "") or ""
        normalized = distribution_name.lower().replace("_", "-")
        if not normalized.startswith(EXTENSION_DISTRIBUTION_PREFIX):
            logger.warning(
                "Ignoring entry point %s=%s: admin extensions must come from a %s* distribution",
                entry_point.name,
                entry_point.value,
                EXTENSION_DISTRIBUTION_PREFIX,
            )
            continue
        if normalized in blocked or entry_point.name.lower() in blocked:
            logger.info("Admin extension %s is disabled by configuration", entry_point.name)
            continue
        try:
            loaded = entry_point.load()
        except Exception as exc:
            raise ExtensionError(f"Cannot load admin extension {entry_point.name!r}: {exc}") from exc
        extension = loaded() if isinstance(loaded, type) else loaded
        if not isinstance(extension, AdminExtension):
            raise TypeError(f"Entry point {entry_point.name!r} did not resolve to an AdminExtension")
        extensions.append(extension)
    return extensions
