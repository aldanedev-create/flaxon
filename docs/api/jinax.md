
# Jinax API

## Jinax

Jinax is the Flaxon template engine for server-rendered applications.

### Constructor

```python
Jinax(
    template_directory: str | Path = "templates",
    *,
    auto_reload: bool = False,
    strict_undefined: bool = True,
    globals: dict[str, Any] | None = None,
    filters: dict[str, Callable[..., Any]] | None = None
)
````

### Methods

#### add_global

```python
def add_global(name: str, value: Any) -> None
```

Add a global variable available inside templates.

---

#### add_filter

```python
def add_filter(name: str, func: Callable[..., Any]) -> None
```

Add a custom template filter.

---

#### render

```python
async def render(
    template_name: str,
    context: dict[str, Any] | None = None
) -> str
```

Render a template and return the generated HTML string.

---

#### render_response

```python
async def render_response(
    template_name: str,
    context: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None
) -> HTMLResponse
```

Render a template and return an HTML response object.

---

# Environment

Template rendering environment.

## Constructor

```python
Environment(
    loader: Any,
    autoescape: bool = True,
    enable_async: bool = True,
    auto_reload: bool = False,
    strict_undefined: bool = False
)
```

## Methods

### add_global

```python
def add_global(name: str, value: Any) -> None
```

Register a global value.

---

### add_filter

```python
def add_filter(name: str, func: Callable[..., Any]) -> None
```

Register a template filter.

---

### get_template

```python
def get_template(name: str) -> Any
```

Load a template by name.

---

### from_string

```python
def from_string(source: str) -> Any
```

Create a template from a string.

---

# Loader

Template file loader.

## Constructor

```python
Loader(
    search_path: str | Path,
    encoding: str = "utf-8"
)
```

## Methods

### get_source

```python
def get_source(
    environment: Any,
    template: str
) -> tuple[str, str | None, Callable[[], bool] | None]
```

Get template source information.

---

### list_templates

```python
def list_templates() -> list[str]
```

Return all available templates.

---

# TemplateNotFound

Exception raised when a template cannot be found.

```python
TemplateNotFound(template: str)
```

## Attributes

| Attribute | Type | Description           |
| --------- | ---- | --------------------- |
| template  | str  | Missing template name |

---

# Filters

## currency

```python
currency(
    value: Any,
    code: str = "USD"
) -> str
```

Format a number as currency.

Example:

```jinax
{{ price|currency("USD") }}
```

Output:

```
$29.99
```

---

# Built-in Filters

| Filter     | Description              |
| ---------- | ------------------------ |
| capitalize | Capitalize a string      |
| lower      | Convert to lowercase     |
| upper      | Convert to uppercase     |
| title      | Convert to title case    |
| trim       | Remove whitespace        |
| escape     | Escape HTML              |
| safe       | Mark content as safe     |
| json       | Convert value to JSON    |
| length     | Get length               |
| reverse    | Reverse a string or list |
| join       | Join list items          |
| replace    | Replace text             |
| date       | Format date              |
| datetime   | Format datetime          |
| currency   | Format currency          |
| truncate   | Shorten text             |
| default    | Provide default value    |
| first      | Get first item           |
| last       | Get last item            |

---

# Built-in Functions

| Function               | Description               |
| ---------------------- | ------------------------- |
| `now()`                | Current datetime          |
| `date()`               | Current date              |
| `datetime()`           | Current datetime          |
| `range(n)`             | Create number range       |
| `length(value)`        | Get length                |
| `type(value)`          | Get value type            |
| `str(value)`           | Convert to string         |
| `int(value)`           | Convert to integer        |
| `float(value)`         | Convert to float          |
| `bool(value)`          | Convert to boolean        |
| `list(value)`          | Convert to list           |
| `dict(value)`          | Convert to dictionary     |
| `json(value)`          | Convert to JSON           |
| `random()`             | Generate random float     |
| `random_int(min, max)` | Generate random integer   |
| `random_choice(items)` | Select random item        |
| `uuid()`               | Generate UUID             |
| `hash(value)`          | Hash a value              |
| `env(key, default)`    | Read environment variable |

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
