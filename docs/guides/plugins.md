# Plugins

## Overview

Flaxon includes a powerful plugin system that allows applications and third-party packages to extend the framework without modifying the core.

Plugins can provide:

- Routes
- Middleware
- CLI commands
- Events
- Health checks
- Background tasks
- Database integrations
- Authentication providers
- Template extensions
- GraphQL extensions
- WebSocket handlers
- Configuration defaults

Plugins can be loaded manually, automatically, or discovered from installed Python packages.

---

# Creating a Plugin

## Basic Plugin

```python
from flaxon.plugins import Plugin

class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "Example Flaxon plugin"

    def setup(self, app):
        @app.get("/plugin")
        async def plugin():
            return {
                "plugin": self.name,
                "version": self.version,
            }
```

Register the plugin:

```python
from flaxon import Flaxon
from flaxon.plugins import PluginManager

app = Flaxon("my-app")

manager = PluginManager(app)
await manager.load_plugin(MyPlugin())
```

---

# Plugin Directory

A common project layout is:

```text
project/
│
├── app.py
│
├── plugins/
│   ├── __init__.py
│   ├── auth.py
│   ├── payments.py
│   ├── analytics.py
│   └── monitoring.py
│
└── config.py
```

Large plugins can use their own package:

```text
plugins/
└── analytics/
    ├── __init__.py
    ├── plugin.py
    ├── middleware.py
    ├── routes.py
    ├── cli.py
    ├── events.py
    ├── health.py
    └── templates/
```

---

# Plugin Metadata

Every plugin exposes metadata.

```python
class AnalyticsPlugin(Plugin):

    name = "analytics"

    version = "1.2.0"

    description = "Application analytics"

    author = "Flaxon Team"

    homepage = "https://example.com"

    license = "MIT"
```

---

# Plugin Lifecycle

Plugins receive lifecycle events from the framework.

```python
class LifecyclePlugin(Plugin):

    name = "lifecycle"

    def on_load(self):
        print("Loaded")

    def setup(self, app):
        print("Setup")

    async def on_startup(self):
        print("Application started")

    async def on_shutdown(self):
        print("Application shutting down")

    def on_unload(self):
        print("Plugin unloaded")
```

Lifecycle order:

```
Load
↓

Setup
↓

Startup
↓

Running

↓

Shutdown

↓

Unload
```

---

# Simple Plugins

For small plugins a helper class is available.

```python
from flaxon.plugins import SimplePlugin

def setup(app):

    @app.get("/hello")
    async def hello():
        return {"hello": "world"}

plugin = SimplePlugin(
    "hello-plugin",
    setup,
)
```

---

# Loading Plugins

## Load One Plugin

```python
manager.load_plugin(MyPlugin())
```

## Load Multiple Plugins

```python
manager.load_plugins(
    [
        AuthPlugin(),
        CachePlugin(),
        AnalyticsPlugin(),
    ]
)
```

## Load From Directory

```python
await manager.load_plugins_from_path("plugins")
```

## Load From Python Module

```python
await manager.load_plugins_from_module(
    "myproject.plugins"
)
```

## Load Everything

```python
await manager.load_all_plugins()
```

---

# Plugin Discovery

Flaxon can automatically discover plugins installed into Python.

```python
manager.auto_discover()
```

Discovered plugins are loaded in dependency order.

---

# Plugin Dependencies

Plugins can depend on one another.

```python
class DatabasePlugin(Plugin):

    name = "database"

    provides = [
        "database"
    ]
```

```python
class AuthPlugin(Plugin):

    name = "auth"

    requires = [
        "database"
    ]
```

Flaxon validates dependencies before loading plugins.

If a dependency is missing, startup fails with a clear error message.

---

# Optional Dependencies

```python
class MetricsPlugin(Plugin):

    optional = [
        "redis",
        "prometheus",
    ]
```

The plugin still loads if optional dependencies are unavailable.

---

# Plugin Configuration

Plugins can read application configuration.

```python
class MailPlugin(Plugin):

    def setup(self, app):

        self.host = app.config.get(
            "MAIL_HOST"
        )

        self.port = app.config.get(
            "MAIL_PORT",
            25,
        )
```

---

# Plugin State

Plugins can store shared application state.

```python
class CachePlugin(Plugin):

    def setup(self, app):

        app.state.cache = {}
```

Later:

```python
cache = app.state.cache
```

---

# Plugin Routes

```python
class BlogPlugin(Plugin):

    def setup(self, app):

        @app.get("/blog")
        async def posts():
            return []
```

---

# Plugin Middleware

```python
from flaxon.middleware import Middleware

class HeaderMiddleware(Middleware):

    async def __call__(self, scope, receive, send):

        async def wrapper(message):

            if message["type"] == "http.response.start":
                headers = list(message["headers"])
                headers.append(
                    (
                        b"x-plugin",
                        b"enabled",
                    )
                )
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, wrapper)
```

Register:

```python
app.add_middleware(HeaderMiddleware)
```

---

# Plugin CLI Commands

```python
from flaxon.cli import Command

class HelloCommand(Command):

    name = "hello"

    help_text = "Example command"

    def run(self, args):

        print("Hello Plugin")
```

Register:

```python
app.cli.add_command(
    HelloCommand()
)
```

---

# Plugin Events

Plugins can subscribe to application events.

```python
@app.events.listener("user.created")
async def created(event):

    print(event.data)
```

Emit events:

```python
await app.events.emit(
    "user.created",
    {
        "username": "alice"
    }
)
```

---

# Plugin Hooks

Plugins can expose reusable hooks.

```python
app.plugin_hooks.register(
    "before_response",
    callback,
)
```

Trigger:

```python
await app.plugin_hooks.trigger_async(
    "before_response",
    response,
)
```

---

# Plugin Health Checks

```python
class RedisPlugin(Plugin):

    def setup(self, app):

        app.health.register(
            "redis",
            self.check,
        )

    async def check(self):

        return {
            "status": "healthy"
        }
```

Health endpoint:

```
GET /health
```

---

# Background Tasks

Plugins can register scheduled jobs.

```python
@app.scheduler.every(minutes=5)
async def cleanup():

    ...
```

---

# Database Plugins

```python
class PostgreSQLPlugin(Plugin):

    def setup(self, app):

        @app.on_startup
        async def connect():
            ...

        @app.on_shutdown
        async def disconnect():
            ...
```

---

# Plugin Manager

```python
manager = PluginManager(app)

manager.list_plugins()

manager.get_plugin("analytics")

manager.is_loaded("analytics")

manager.unload_plugin("analytics")

manager.reload_plugin("analytics")
```

---

# Best Practices

- Keep plugins focused on one responsibility.
- Declare dependencies explicitly.
- Validate configuration during setup.
- Avoid global state.
- Clean up resources during shutdown.
- Use semantic versioning.
- Document configuration options.
- Register health checks when possible.
- Handle startup failures gracefully.
- Write automated tests for plugins.

---

# Complete Example

```python
from flaxon import Flaxon
from flaxon.plugins import PluginManager

app = Flaxon("plugin-demo")

manager = PluginManager(app)

await manager.load_plugins_from_path(
    "plugins"
)

@app.get("/")
async def home():
    return {
        "plugins": manager.list_plugins()
    }
```

Example response:

```json
{
  "plugins": [
    "database",
    "authentication",
    "redis",
    "graphql",
    "analytics"
  ]
}
```
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
