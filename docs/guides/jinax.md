# Jinax Templates

## Overview

Jinax is Flaxon's optional server-side template engine powered by Jinja2.

It provides modern HTML rendering while integrating seamlessly with Flaxon's async-first architecture.

### Features

- Server-side HTML rendering
- Template inheritance
- Automatic HTML escaping
- Async rendering
- Custom filters
- Custom global functions
- Template caching
- Hot reloading during development
- Macros
- Includes
- Layouts
- Jinja2 template caching and configurable reload behavior

---

# Installation

Install Flaxon with template support:

```bash
pip install flaxon[templates]
```

---

# Setup

Configure Jinax with your application.

```python
from flaxon import Flaxon
from flaxon.jinax import Jinax


app = Flaxon("website")


app.use_templates(

    Jinax(
        "templates",
        auto_reload=True
    )

)
```

---

# Project Structure

A typical project looks like:

```text
project/

├── app.py
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── contact.html
│   ├── macros.html
│   └── partials/
│       ├── navbar.html
│       └── footer.html
└── static/
    ├── css/
    ├── js/
    └── images/
```

---

# Rendering Templates

Templates are rendered using the request object.

```python
@app.get("/")
async def home(request):

    return await request.render(

        "home.html",

        {
            "title": "Home",

            "name": "World",

            "items": [
                "Routing",
                "Templates",
                "Validation"
            ]
        }

    )
```

---

# Your First Template

Create:

```
templates/home.html
```

```html
<!DOCTYPE html>

<html>

<head>

    <title>{{ title }}</title>

</head>

<body>

    <h1>
        Welcome {{ name }}!
    </h1>

    <ul>

        {% for item in items %}

            <li>{{ item }}</li>

        {% endfor %}

    </ul>

</body>

</html>
```

---

# Complete copy-paste application

Create `app.py`:

```python
from flaxon import Flaxon
from flaxon.jinax import Jinax

app = Flaxon("jinax-example", debug=True)
app.use_templates(Jinax("templates", auto_reload=True))

@app.get("/")
async def home(request):
    return await request.render("home.html", {
        "title": "Jinax",
        "items": ["Routing", "Validation", "Templates"],
    })
```

Create `templates/home.html`:

```html
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{{ title }}</title></head>
<body><h1>{{ title }}</h1>
<ul>
    {% for item in items %}
    <li>{{ item }}</li>
    {% endfor %}
    </ul>
</body>
</html>
```

Run `pip install "flaxon[templates]"` and then `flaxon run app:app --reload`.
Jinax uses Jinja2 autoescaping for HTML templates. Keep database queries and
permission decisions in routes/services and pass prepared view data to templates.

---

# Template Inheritance

Inheritance allows pages to share a common layout.

## Base Template

```
templates/base.html
```

```html
<!DOCTYPE html>

<html>

<head>

    <title>

        {% block title %}
            Flaxon
        {% endblock %}

    </title>

</head>

<body>

<header>

    {% block header %}

        Default Header

    {% endblock %}

</header>

<main>

    {% block content %}

    {% endblock %}

</main>

<footer>

    {% block footer %}

        Copyright © 2026

    {% endblock %}

</footer>

</body>

</html>
```

---

## Child Template

```
templates/home.html
```

```html
{% extends "base.html" %}

{% block title %}

Home

{% endblock %}


{% block header %}

Welcome

{% endblock %}


{% block content %}

<h1>{{ heading }}</h1>

<p>{{ description }}</p>

{% endblock %}
```

---

# Including Templates

Reusable components can be included.

```html
{% include "partials/navbar.html" %}

<h1>Home</h1>

{% include "partials/footer.html" %}
```

---

# Built-in Filters

Jinax includes many commonly used filters.

| Filter | Description |
|---------|-------------|
| `capitalize` | Capitalize text |
| `lower` | Convert to lowercase |
| `upper` | Convert to uppercase |
| `title` | Title case |
| `trim` | Remove whitespace |
| `escape` | Escape HTML |
| `safe` | Mark content as safe |
| `json` | Convert to JSON |
| `length` | Count items |
| `reverse` | Reverse a sequence |
| `join` | Join list items |
| `replace` | Replace text |
| `default` | Default value |
| `first` | First item |
| `last` | Last item |
| `truncate` | Shorten text |
| `date` | Format dates |
| `datetime` | Format date and time |
| `currency` | Format currency |

---

# Filter Examples

```html
{{ name|capitalize }}

{{ username|lower }}

{{ price|currency("USD") }}

{{ description|truncate(100) }}

{{ tags|join(", ") }}

{{ created_at|datetime("%Y-%m-%d %H:%M") }}
```

---

# Custom Filters

Create your own filters.

```python
jinax = Jinax(
    "templates"
)


def currency_filter(
    value,
    symbol="$"
):

    return f"{symbol}{value:,.2f}"


jinax.add_filter(

    "currency",

    currency_filter

)
```

Using the filter:

```html
<p>

Price:

{{ product.price|currency("$") }}

</p>
```


---

# Global Functions

Global functions can be registered and used directly inside templates.

```python
jinax = Jinax(
    "templates"
)


def get_user(username):

    return {
        "name": username,
        "email": f"{username}@example.com"
    }


jinax.add_global(
    "get_user",
    get_user
)
```

Using the function:

```html
{% set user = get_user("alice") %}

<h2>{{ user.name }}</h2>

<p>{{ user.email }}</p>
```

---

# Global Variables

Global variables are available in every template.

```python
jinax.add_global(
    "site_name",
    "Flaxon"
)

jinax.add_global(
    "version",
    "0.1.0"
)
```

Template:

```html
<footer>

{{ site_name }}

Version {{ version }}

</footer>
```

---

# Macros

Macros allow reusable template components.

Create:

```
templates/macros.html
```

```html
{% macro render_card(title, content, color="blue") %}

<div class="card card-{{ color }}">

    <h3>{{ title }}</h3>

    <p>{{ content }}</p>

</div>

{% endmacro %}
```

Using the macro:

```html
{% import "macros.html" as macros %}

{{ macros.render_card(

    "Welcome",

    "Hello from Jinax",

    "green"

) }}
```

---

# Control Statements

Jinax supports standard template control statements.

Loop:

```html
<ul>

{% for product in products %}

    <li>

        {{ product.name }}

    </li>

{% endfor %}

</ul>
```

Conditional:

```html
{% if user %}

    <h2>

        Welcome {{ user.name }}

    </h2>

{% else %}

    <h2>

        Welcome Guest

    </h2>

{% endif %}
```

---

# Async Rendering

Jinax fully supports asynchronous rendering.

```python
@app.get("/dashboard")
async def dashboard(request):

    users = await database.get_users()

    return await request.render(

        "dashboard.html",

        {

            "users": users

        }

    )
```

---

# Hot Reloading

During development templates can automatically reload.

```python
app.use_templates(

    Jinax(

        "templates",

        auto_reload=True

    )

)
```

Hot reloading should normally be disabled in production.

---

# Template Caching

Enable template caching for production deployments.

```python
jinax = Jinax(

    "templates",

    cache_size=100

)
```

Larger applications may increase the cache size.

---

# Autoescaping

Jinax automatically escapes HTML output to reduce XSS risks.

Example:

```html
{{ username }}
```

Output:

```
<script>alert("XSS")</script>
```

becomes

```html
&lt;script&gt;alert("XSS")&lt;/script&gt;
```

---

# Safe HTML

Only mark trusted HTML as safe.

```html
{{ article.body|safe }}
```

Avoid using `safe` with untrusted user input.

---

# Static Files

Reference static assets inside templates.

```html
<link
    rel="stylesheet"
    href="/static/css/style.css"
>

<script
    src="/static/js/app.js"
></script>
```

---

# Complete Example

```python
from datetime import datetime

from flaxon import Flaxon

from flaxon.jinax import Jinax


app = Flaxon(
    "website-demo"
)


app.use_templates(

    Jinax(

        "templates",

        auto_reload=True

    )

)


jinax = app.jinax


def currency(
    value,
    symbol="$"
):

    return f"{symbol}{value:,.2f}"


jinax.add_filter(
    "currency",
    currency
)


def now():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


jinax.add_global(
    "now",
    now
)


@app.get("/")
async def home(request):

    products = [

        {
            "name": "Laptop",
            "price": 999.99
        },

        {
            "name": "Keyboard",
            "price": 49.99
        },

        {
            "name": "Mouse",
            "price": 19.99
        }

    ]


    return await request.render(

        "home.html",

        {

            "title": "Store",

            "products": products

        }

    )
```

Example template:

```
templates/home.html
```

```html
{% extends "base.html" %}

{% block title %}

{{ title }}

{% endblock %}


{% block content %}

<h1>

Welcome to our Store

</h1>

<div class="products">

{% for product in products %}

<div class="product">

    <h3>

        {{ product.name }}

    </h3>

    <p>

        {{ product.price|currency("$") }}

    </p>

</div>

{% endfor %}

</div>

<p>

Generated:

{{ now() }}

</p>

{% endblock %}
```

---

# Security

Jinax enables HTML autoescaping by default.

Recommended practices:

- Keep autoescaping enabled.
- Never trust user-generated HTML.
- Only use the `safe` filter with trusted content.
- Validate all user input.
- Use Content Security Policy (CSP) where appropriate.
- Sanitize uploaded HTML before rendering.

---

# Performance Tips

For production deployments:

- Enable template caching.
- Disable hot reloading.
- Reuse template environments.
- Cache expensive database queries.
- Minimize complex template logic.
- Perform heavy processing inside Python instead of templates.

---

# Debugging

When Flaxon runs in debug mode, template errors appear in the Debug Dashboard.

Open:

```
http://localhost:8000/__debug__
```

The debugger records:

- Template syntax errors
- Missing templates
- Undefined variables
- Rendering exceptions
- Stack traces
- Request information
- Error history

Sensitive information is automatically redacted.

---

# Best Practices

- Keep business logic inside Python.
- Keep templates focused on presentation.
- Use template inheritance.
- Reuse components with macros and includes.
- Organize templates into folders.
- Prefer descriptive template names.
- Enable caching in production.
- Use async rendering when loading data.

---

# Recommended Project Structure

```text
project/

├── app.py
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── contact.html
│   ├── macros.html
│   ├── layouts/
│   ├── partials/
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   └── footer.html
│   ├── auth/
│   ├── admin/
│   ├── errors/
│   └── emails/
└── static/
    ├── css/
    ├── js/
    ├── fonts/
    └── images/
```

---

# API Reference

See the Jinax API Reference for complete documentation of:

- Jinax
- Template rendering
- Filters
- Globals
- Macros
- Async rendering
- Template caching
- Autoescaping

---

# Next Steps

Continue with:

- Authentication
- Databases
- Security
- Performance
- Debugging
- GraphQL
- Deployment
- Architecture
