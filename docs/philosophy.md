
# Philosophy

## Core Principles

Flaxon is built around a set of principles that guide its design, development, and long-term direction.

The goal is to create a full-stack framework that is:

- Simple to start
- Powerful when applications grow
- Technology-neutral
- Easy to debug
- Designed for modern async applications

---

# 1. Simple Applications Remain Simple

Small applications should be easy to create without generators, complex configuration, or mandatory architecture.

Flaxon provides a minimal entry point that allows developers to build quickly.

Example:

```python
from flaxon import Flaxon

app = Flaxon("my-app")


@app.get("/")
async def home():
    return {
        "message": "Hello"
    }
````

A simple application should remain simple.

---

# 2. Large Applications Gain Structure

As applications grow, Flaxon provides optional structure without forcing developers into a specific architecture.

Developers can gradually introduce:

* Routers
* Services
* Middleware
* Plugins
* Dependency management

Example:

```python
from flaxon import Router


api = Router(prefix="/api/v1")


@api.get("/users")
async def list_users():
    return [
        {
            "id": 1,
            "name": "Alice"
        }
    ]


app.include_router(api)
```

The framework should grow with the application.

---

# 3. HTML Rendering is Optional

Flaxon treats APIs and backend services as a first-class use case.

HTML rendering through Jinax is optional and loaded only when needed.

## API Only

No template dependencies are required:

```python
@app.get("/api/users")
async def get_users():
    return [
        {
            "id": 1,
            "name": "Alice"
        }
    ]
```

## Using Templates

Templates can be added when required:

```python
from flaxon.jinax import Jinax


app.use_templates(
    Jinax("templates")
)
```

Developers can choose between API-only applications or server-rendered applications.

---

# 4. Technology Neutrality

Flaxon does not force developers to use a specific frontend, database, ORM, or client technology.

You can use:

## Frontend

* React
* Vue
* Angular
* Svelte
* Flutter
* Native mobile applications
* Custom clients

## Databases

* PostgreSQL
* MySQL
* MongoDB
* Redis
* SQLite
* Custom storage solutions

## ORMs and Data Tools

* SQLAlchemy
* SQLModel
* Tortoise ORM
* PyMongo
* Custom solutions

The framework should adapt to your technology choices, not restrict them.

---

# 5. Explicit and Debuggable

Framework behavior should be clear and understandable.

Flaxon avoids unnecessary hidden behavior and focuses on:

* Clear APIs
* Useful error messages
* Debugging information
* Request context visibility

Example:

```python
raise HTTPException(
    404,
    "User not found.",
    code="FX-USER-404"
)
```

Errors should help developers understand what happened and how to fix it.

---

# Design Decisions

## Why ASGI?

ASGI (Asynchronous Server Gateway Interface) is the modern Python standard for asynchronous web servers.

It provides support for:

* HTTP requests
* WebSockets
* Application lifecycle events

This makes it a strong foundation for async-first applications.

---

## Why Flask-Style Routes?

Flask-style decorators are familiar to many Python developers.

They provide:

* Simple syntax
* High readability
* Easy learning curve
* Clear application structure

Example:

```python
@app.get("/users")
async def users():
    return []
```

---

## Why Async-First?

Modern applications often depend on external resources:

* Databases
* APIs
* File storage
* WebSocket connections

Async programming allows applications to efficiently handle many concurrent operations.

This is useful for:

* Real-time applications
* Chat systems
* Dashboards
* Mobile backends
* API platforms

---

## Why No Built-in ORM?

Flaxon is technology-neutral.

Different projects require different database approaches, so developers should choose the tools that fit their application.

Flaxon supports using:

* SQL databases
* NoSQL databases
* ORMs
* Query builders
* Custom database layers

---

# What Flaxon Is Not

Flaxon is designed with a specific purpose.

It is:

* Not a full-stack framework with every feature built in.
* Not a replacement for Node.js, Go, Rust, or other ecosystems.
* Not designed to claim absolute performance superiority.
* Not a compiled language.

Flaxon is Python with the advantages and tradeoffs that come with Python.

---

# When to Use Flaxon

Flaxon is a good choice for:

* Building APIs for React, Vue, Angular, or other frontends
* Developing mobile application backends
* Creating real-time applications with WebSockets
* Building Python microservices
* Creating scalable backend systems
* Projects that value technology freedom
* Teams that want clear debugging
* Applications that start small and grow over time

---

# When Not to Use Flaxon

Flaxon may not be the best choice when:

* You are creating only a simple static website.
* You require maximum CPU performance from a compiled language.
* You need an ecosystem with decades of existing packages and integrations.

---

# The Flaxon Vision

Flaxon aims to provide a modern Python backend experience:

**Simple enough for beginners.
Powerful enough for production.
Flexible enough for any technology stack.**



## Integrated interfaces, explicit choices

Teloce is Flaxon's integrated component/compiler path. Python routes, UI pages
and scoped components can live in a single feature module. Jinax remains the
server-template path, and external frontends remain possible. Full-stack here
means an integrated application workflow, not automatic hosting, SSR or accounts.
See the [ten lessons](fullstack/index.md).
