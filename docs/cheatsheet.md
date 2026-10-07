
# Flaxon & Plugins - Quick Reference Cheat Sheet

A quick reference guide for the Flaxon Python full-stack framework and official plugins.

---

# 📦 Installation

## Core Framework

```bash
pip install flaxon
````

## Standard Features

```bash
pip install "flaxon[standard]"
```

## Plugins

```bash
pip install flaxon-ai[all]
pip install flaxon-mobile[all]
pip install flaxon-inertia
pip install flaxon-oauth-google
pip install flaxon-fyr
pip install flaxon-debug-toolbar
pip install flaxon-sentry
pip install flaxon-pytest
pip install flaxon-spring-boot
pip install flaxon-ffd
```

---

````

---

## Fixed Core Commands Section

```markdown
# 🚀 Core Flaxon Commands

```bash
# Create project
flaxon new my-app

# Run application
flaxon run app:app

# Development mode
flaxon run app:app --reload

# Show routes
flaxon routes app:app

# Diagnose application
flaxon doctor app:app

# Generate route
flaxon generate route /api/users --method GET

# Generate schema
flaxon generate schema CreateUser
````

---

````

---

## Fixed Basic Application

Problems fixed:
- Removed unnecessary uvicorn usage.
- Added proper `request` typing consistency.
- Fixed websocket example formatting.

```markdown
# 📝 Basic Application

```python
from flaxon import Flaxon


app = Flaxon(
    "my-app",
    debug=True
)


@app.get("/")
async def home():
    return {
        "message": "Hello, World!"
    }


@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {
        "id": user_id,
        "name": f"User {user_id}"
    }


@app.post("/users")
async def create_user(request):
    data = await request.json()

    return {
        "success": True,
        "data": data
    }


@app.websocket("/ws/echo")
async def echo(socket):

    await socket.accept()

    async for message in socket.iter_json():
        await socket.send_json({
            "echo": message
        })
````

Run:

```bash
flaxon run app:app --reload
```

---

````

---

## Fixed Validation Section

```markdown
# 🔧 Validation Schemas

```python
from flaxon.validation import Schema, fields


class CreateUser(Schema):

    name = fields.StrField(
        required=True,
        min_length=2,
        max_length=80
    )

    email = fields.EmailField(
        required=True
    )

    age = fields.IntField(
        required=False,
        minimum=13,
        maximum=120
    )

    status = fields.ChoiceField(
        choices=[
            "active",
            "inactive",
            "pending"
        ]
    )


@app.post("/users")
async def create_user(data: CreateUser):

    return {
        "success": True,
        "user": data.to_dict()
    }
````

---

````

---

## Fixed Middleware

```markdown
# 🛡️ Middleware

```python
from flaxon.middleware import CORSMiddleware
from flaxon.security import RateLimitMiddleware


app.add_middleware(
    CORSMiddleware,
    allowed_origins=[
        "https://example.com"
    ],
    allow_credentials=True,
)


app.add_middleware(
    RateLimitMiddleware,
    requests=120,
    window_seconds=60,
)
````

---

````

---

## Fixed AI Plugin Example

Changes:
- Added missing `os`.
- Made import style consistent.

```markdown
## 🤖 flaxon-ai

```python
import os

from flaxon_ai import FlaxonAIPlugin


await app.plugins.load_plugin(
    FlaxonAIPlugin(
        provider="gemini",
        api_key=os.environ.get(
            "GEMINI_API_KEY"
        ),
    )
)


response = await app.state.ai.generate(
    "Write a poem about Python"
)


async for chunk in app.state.ai.stream(
    "Tell a story"
):
    print(chunk)
````

---

````

---

## Fixed Quick Start Template

```markdown
# 🚀 Quick Start Template

```python
import os

from flaxon import Flaxon
from flaxon_ai import FlaxonAIPlugin
from flaxon_debug_toolbar import DebugToolbarPlugin


app = Flaxon(
    "my-app",
    debug=True
)


await app.plugins.load_plugin(
    DebugToolbarPlugin()
)


await app.plugins.load_plugin(
    FlaxonAIPlugin(
        provider="gemini",
        api_key=os.environ.get(
            "GEMINI_API_KEY"
        ),
    )
)


@app.get("/")
async def home():

    return {
        "message": "Hello, Flaxon!"
    }


@app.get("/ai")
async def ai_generate():

    result = await app.state.ai.generate(
        "Say hello"
    )

    return {
        "response": result
    }
````

Run:

```bash
flaxon run app:app --reload
```

---

````

---

## Fixed Resources Section

```markdown
# 📚 Useful Resources

| Resource | Link |
|---|---|
| Flaxon Website | https://flaxon-website.vercel.app |
| Documentation | https://flaxon-website.vercel.app/docs |
| GitHub | https://github.com/aldanedev-create/Flaxon-Backend-Framework |
| PyPI | https://pypi.org/project/flaxon |
| VS Code Extension | https://marketplace.visualstudio.com |

---
````
