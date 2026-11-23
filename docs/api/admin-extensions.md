# Admin extension API

Generated from `flaxon.admin.extensions` by `scripts/generate_admin_extension_docs.py`.
Do not edit by hand: run the script (or `python scripts/generate_admin_extension_docs.py --check`).

## `ADMIN_EXTENSION_GROUP`

Constant: `flaxon.admin`.

## `AdminExtension`

`class AdminExtension(*, root: str | pathlib.Path | None = None) -> None`

Base class for a ``flaxon-admin-*`` package.

### `bind`

`bind(dashboard: Any) -> None`

Attach the extension to a dashboard (called once by the registry).

### `cards`

`cards() -> list[metrics.Metric]`

Return dashboard cards contributed by this extension.

### `component`

`component(filename: str) -> Component`

Return (and cache) the component stored in ``ui/<filename>``.

### `components`

`components() -> list[Component]`

Return every component in ``ui/`` plus any declared out of tree.

### `fields`

`fields() -> list[type[resources.Field]]`

Return custom field classes contributed by this extension.

### `model_registered`

`model_registered(dashboard: Any, admin_model: Any) -> None`

Called when a model is registered after the extension was loaded.

### `pages`

`pages() -> list[ExtensionPage]`

Return custom admin pages contributed by this extension.

### `setup`

`setup(dashboard: Any) -> None`

Optional hook for permissions or other registration work.

### `tools`

`tools() -> list[Tool]`

Return tools shown on the admin dashboard.

## `Component`

`class Component(name: str, source: str | pathlib.Path) -> None`

One ``.vel`` single-file component owned by an extension.

### `compile`

`compile() -> str`

Compile the component to a JavaScript ES module (cached).

### `mount_point`

`mount_point(props: dict[str, typing.Any] | None = None, *, value: Any = None, body: str = ) -> str`

Return the escaped mount element the browser bundle enhances.

### `render`

`render(props: dict[str, typing.Any] | None = None) -> str`

Render the component to HTML on the server (no browser script runs).

## `EXTENSION_DISTRIBUTION_PREFIX`

Constant: `flaxon-admin-`.

## `ExtensionError`

`class ExtensionError`

Raised when an admin extension cannot be loaded or compiled.

## `ExtensionPage`

`class ExtensionPage(name: str, component: Component, *, label: str | None = None, url: str | None = None, permission: str = admin.view_dashboard, icon: str = fa-puzzle-piece, category: str = Extensions, description: str = , props: Any = None, methods: set[str] | None = None) -> None`

A custom admin page rendered from a Teloce component.

### `bind`

`bind(dashboard: Any) -> None`

Remember the dashboard used by :meth:`handler`.

### `build_props`

`build_props(request: Any) -> dict[str, typing.Any]`

Evaluate the page's props for ``request`` (sync or async callables).

### `handler`

`handler(request: Any) -> Any`

Render the page through the dashboard's Jinax environment.

## `ExtensionRegistry`

`class ExtensionRegistry(dashboard: Any) -> None`

Owns extension discovery, validation, compilation and asset serving.

### `asset_url`

`asset_url(name: str) -> str`

Return the admin-relative URL of one compiled component.

### `build`

`build() -> None`

Compile every component once; fail early on a broken extension.

### `bundle`

`bundle() -> str`

Return the ES module that mounts every component on the page.

### `code`

`code(name: str) -> str`

Return the compiled JavaScript for a component.

### `component`

`component(name: str) -> Component`

Return a registered component by name.

### `load`

`load(*, include: collections.abc.Iterable[AdminExtension] | None = None) -> list[AdminExtension]`

Discover ``flaxon-admin-*`` entry points and register the results.

### `register`

`register(extension: AdminExtension) -> AdminExtension`

Bind and register one extension; contributions are added immediately.

## `TeloceCard`

`class TeloceCard(title: str, component: Component, *, calculate: Any, props: Any = None, **options: Any) -> None`

A dashboard card whose markup is a Teloce component.

### `calculate`

`calculate(request: Any = None, *, now: Any = None) -> dict[str, typing.Any]`

Return the card data, awaiting the callable when needed.

### `render`

`render(data: dict[str, typing.Any]) -> str`

Render the component on the server and return its mount point.

## `TeloceField`

`class TeloceField(name: str, component: Component, *, props: dict[str, typing.Any] | None = None, fallback: str = text, fallback_choices: collections.abc.Iterable[tuple[typing.Any, str]] = (), **options: Any) -> None`

A form field whose control is a Teloce component.

### `props_for`

`props_for(value: Any = None) -> dict[str, typing.Any]`

Return the props passed to the component for ``value``.

### `schema_entry`

`schema_entry() -> dict[str, typing.Any]`

Expose the component and its static props to the field template.

## `Tool`

`class Tool(label: str, page: ExtensionPage, *, icon: str = fa-toolbox, description: str = , permission: str | None = None) -> None`

A dashboard shortcut contributed by an extension.

## `load_extensions`

`load_extensions(*, group: str = flaxon.admin, disabled: collections.abc.Iterable[str] = (), entry_points: Any = None) -> list[AdminExtension]`

Load extensions from installed ``flaxon-admin-*`` distributions.
