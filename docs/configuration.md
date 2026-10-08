# Configuration

## Generated projects: settings.py

Use `Flaxon.from_settings("settings")` in `app.py`. Both the application and
`management.py` read this same module. `env.load()` reads `.env`; existing process
environment variables take precedence. Only values read with `env.str()`,
`env.bool()`, or `env.list()` are taken from the environment in this workflow.
Do not assume every setting automatically maps to a `FLAXON_` variable.

```python
from pathlib import Path
from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
env.load(BASE_DIR / ".env")
PROJECT_NAME = "project_manager"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY")
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{BASE_DIR / 'data/app.sqlite3'}")
ALLOWED_HOSTS = env.list("FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("FLAXON_CSRF_TRUSTED_ORIGINS", default=[])
TIME_ZONE = "UTC"
ADMIN_ENABLED = True
CMS_ENABLED = True
ADMIN_SERVICES_ENABLED = False
ADMIN_STORE_BACKEND = "sqlite"
ADMIN_STORAGE_PATH = BASE_DIR / "data/admin.sqlite3"
```

`DEBUG=False` requires a persistent secret of at least 32 characters and explicit
allowed hosts. Origins include the scheme and host, without a path. Starting the
server opens connections and never changes the model schema. Run `makemigrations`,
review and commit Python migrations, then run `migrate`.

Use `app.settings` for validated project settings. Mount feature modules explicitly
in `app.py`; do not put executable module composition in `settings.py`.

See [ORM and management](guides/orm.md) for PostgreSQL, model discovery, transactions,
Admin registration and the optional ORM metadata store.

## Lower-level configuration

The sections below describe the independent `Flaxon(...)` / `Config` API, retained
for backend-only applications. They do not replace the generated settings workflow.

## Overview

Flaxon provides a flexible configuration system designed for development and production environments.

Configuration values can be loaded from multiple sources, allowing you to keep sensitive settings outside your source code while still providing sensible defaults.

---

# Configuration Sources

Configuration is loaded in the following order (lowest to highest priority):

1. **Default Values** — Built-in framework defaults.
2. **Application Configuration** — Values passed to `Flaxon()` or `Config()`.
3. **Environment Variables** — Variables prefixed with `FLAXON_`.

Environment variables always override default values.

---

# Default Configuration

```python
DEFAULTS = {
    "ENV": "development",
    "DEBUG": False,
    "SECRET_KEY": None,
    "ALLOWED_HOSTS": [
        "localhost",
        "127.0.0.1"
    ],
    "MAX_BODY_SIZE": 10 * 1024 * 1024,
    "TRUSTED_PROXIES": [],
    "PROXY_HEADERS": [
        "x-forwarded-for",
        "x-forwarded-proto",
        "x-forwarded-host",
    ],
}
```

---

# Setting Configuration

## Configure Through Code

Pass configuration values when creating your application.

```python
from flaxon import Flaxon

app = Flaxon(
    "my-app",
    debug=True,
    config={
        "ENV": "production",
        "MAX_BODY_SIZE": 5 * 1024 * 1024,
    },
)
```

---

## Configure Through Environment Variables

Linux/macOS

```bash
export FLAXON_ENV=production
export FLAXON_DEBUG=false
export FLAXON_SECRET_KEY=your-secret-key
```

Windows (PowerShell)

```powershell
$env:FLAXON_ENV="production"
$env:FLAXON_DEBUG="false"
$env:FLAXON_SECRET_KEY="your-secret-key"
```

---

## Using a `.env` File

```env
FLAXON_ENV=production
FLAXON_DEBUG=false
FLAXON_SECRET_KEY=your-secret-key
```

This approach is recommended for local development because it keeps secrets out of your source code.

---

# Accessing Configuration

Configuration values can be accessed in several ways.

```python
# Attribute access
app.config.DEBUG

# Dictionary access
app.config["DEBUG"]

# Safe access
app.config.get("DEBUG")
```

---

# Environment Helpers

Flaxon provides helper methods for checking the current environment.

```python
# Current environment
app.config.get_env()

# Environment checks
app.config.is_development()
app.config.is_testing()
app.config.is_staging()
app.config.is_production()
```

---

# Configuration Helpers

Convenience methods are available for common settings.

```python
app.config.get_secret_key()

app.config.get_allowed_hosts()

app.config.get_max_body_size()
```

---

# Production Configuration

A typical production configuration might look like:

```env
FLAXON_ENV=production
FLAXON_DEBUG=false
FLAXON_SECRET_KEY=<32+ random hex bytes>
FLAXON_ALLOWED_HOSTS=api.example.com,example.com
FLAXON_MAX_BODY_SIZE=10485760
```

---

# Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ENV` | `development` | Current application environment |
| `DEBUG` | `False` | Enables debug mode |
| `SECRET_KEY` | `None` | Secret used for cryptographic operations |
| `ALLOWED_HOSTS` | `localhost, 127.0.0.1` | Allowed hostnames |
| `MAX_BODY_SIZE` | `10 MB` | Maximum request body size |
| `TRUSTED_PROXIES` | `[]` | Trusted reverse proxy addresses |
| `PROXY_HEADERS` | Standard proxy headers | Headers used by reverse proxies |

---

# Security Recommendations

| Setting | Recommendation |
|---------|----------------|
| `DEBUG` | Always set to `False` in production. |
| `SECRET_KEY` | Use at least 32 random bytes and never commit it to source control. |
| `ALLOWED_HOSTS` | Specify only trusted domains. Avoid using wildcards whenever possible. |
| `MAX_BODY_SIZE` | Set an appropriate upload limit for your application. |
| `TRUSTED_PROXIES` | Only trust proxies you control. |

---

# Best Practices

For secure and maintainable applications:

- Keep secrets in environment variables or a `.env` file.
- Never commit production credentials to version control.
- Use different configuration values for development, testing, and production.
- Disable debug mode in production.
- Restrict allowed hosts to your application's domains.
- Review request size limits based on your application's requirements.

---

# Example Production Setup

```python
from flaxon import Flaxon

app = Flaxon(
    "production-api",
    config={
        "ENV": "production",
        "DEBUG": False,
        "MAX_BODY_SIZE": 10 * 1024 * 1024,
    },
)
```

With environment variables:

```env
FLAXON_SECRET_KEY=replace-with-a-secure-random-secret
FLAXON_ALLOWED_HOSTS=api.example.com
```

This keeps sensitive configuration outside your application code while allowing Flaxon to load it automatically at startup.