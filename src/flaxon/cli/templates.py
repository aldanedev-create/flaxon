
from __future__ import annotations

from typing import Any


class TemplateEngine:
    """
    Template engine for generating project files and code components.
    """

    def __init__(self) -> None:
        """Initialize the template engine with default Flaxon templates."""
        self._templates = self._default_templates()

    def _default_templates(self) -> dict[str, str]:
        return {
            "app.py": """from flaxon import Flaxon

app = Flaxon("{name}", debug=True)

@app.get("/")
async def home():
    return {{"message": "Hello from {name}"}}

@app.get("/health")
async def health():
    return {{"status": "healthy", "service": "{name}"}}
""",
            "pyproject.toml": """[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["flaxon-framework[standard]>=0.2.5"]
""",
            "gitignore": """.venv/
__pycache__/
*.pyc
.env
dist/
build/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
""",
            "README.md": """# {name}

A Flaxon application.

## Installation

```bash
python -m pip install -e .

```

## Running

```bash
flaxon run app:app --reload

```

## Testing

```bash
pytest

```

""",
            "controller.py": """from flaxon import Router

router = Router(prefix="/api/{name}")

@router.get("/")
async def index():
    return {{"message": "{name} controller"}}

@router.get("/{id:int}")
async def get(id: int):
    return {{"id": id, "name": "{name}"}}

@router.post("/")
async def create(request):
    data = await request.json()
    return {{"created": True, "data": data}}
""",

            "schema.py": """from flaxon.validation import Schema, fields

class Create{name_capitalize}(Schema):
    name = fields.StrField(required=True, min_length=2, max_length=80)
    email = fields.Email(required=True)
    age = fields.Integer(required=False, minimum=13, maximum=120)


class Update{name_capitalize}(Schema):
    name = fields.StrField(required=False, min_length=2, max_length=80)
    email = fields.Email(required=False)
    age = fields.Integer(required=False, minimum=13, maximum=120)
""",

            "service.py": """class {name_capitalize}Service:
    def __init__(self, db):
        self.db = db

    async def get_all(self):
        return await self.db.fetch_all("SELECT * FROM {name}s")

    async def get_by_id(self, id):
        return await self.db.fetch_one(
            "SELECT * FROM {name}s WHERE id = $1",
            id,
        )

    async def create(self, data):
        return await self.db.fetch_one(
            "INSERT INTO {name}s (name, email) VALUES ($1, $2) RETURNING *",
            data["name"],
            data["email"],
        )

    async def update(self, id, data):
        return await self.db.fetch_one(
            "UPDATE {name}s SET name = $1, email = $2 WHERE id = $3 RETURNING *",
            data["name"],
            data["email"],
            id,
        )

    async def delete(self, id):
        await self.db.execute(
            "DELETE FROM {name}s WHERE id = $1",
            id,
        )
""",

            "middleware.py": """from flaxon.middleware import Middleware

class {name_capitalize}Middleware(Middleware):
    def __init__(self, app, options=None):
        super().__init__(app)
        self.options = options or {}

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        scope["{name}"] = "value"

        async def send_wrapper(message):
            await send(message)

        await self.app(scope, receive, send_wrapper)
""",

 "task.py": """from flaxon.tasks import Task, task
from flaxon.tasks.retry import RetryPolicy


# Define a simple task
@task(name="{name}_task")
async def {name}_task(data: dict) -> dict:
    \"\"\"
    Task to process {name} data.

    Args:
        data: The data to process

    Returns:
        Processed result
    \"\"\"
    # Your task logic here
    result = {"processed": True, "data": data}
    return result


# Define a task with retry policy
@task(
    name="{name}_retry_task",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        max_delay=30.0,
    ),
    timeout=30,
)
async def {name}_retry_task(data: dict) -> dict:
    \"\"\"
    Task with retry policy.

    Args:
        data: The data to process

    Returns:
        Processed result
    \"\"\"
    # Your task logic here
    return {"processed": True, "data": data}


# Define a synchronous task
@task(name="{name}_sync_task")
def {name}_sync_task(value: int) -> int:
    \"\"\"
    Synchronous task.

    Args:
        value: The value to process

    Returns:
        The processed value
    \"\"\"
    return value * 2


# Example: How to use tasks in your application
async def run_{name}_tasks():
    from flaxon.tasks import TaskQueue, TaskRegistry

    # Register tasks
    registry = TaskRegistry()
    registry.register("{name}_task", {name}_task)
    registry.register("{name}_retry_task", {name}_retry_task)
    registry.register("{name}_sync_task", {name}_sync_task)

    # Create queue and push tasks
    queue = TaskQueue()

    # Push a task
    task = Task("{name}_task", {name}_task, args=[{"key": "value"}])
    await queue.push(task)

    # Get result
    result = await queue.get_result(task.id)
    return result
""",



}


    def render(
        self,
        template_name: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Render a registered template by name.
        """
        context = context or {}
        template = self._templates.get(template_name, "")
        return self.render_string(template, context)

    def render_string(
        self,
        template: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Render a template string using the supplied context.
        """
        context = context or {}
        result = template

        flat_context: dict[str, str] = {}

        for key, value in context.items():
            if isinstance(value, str):
                flat_context[key] = value
            elif hasattr(value, "dict") and callable(value.dict):
                for sub_key, sub_value in value.dict().items():
                    flat_context[f"{key}.{sub_key}"] = str(sub_value)
            else:
                flat_context[key] = str(value)

        for key, value in flat_context.items():
            result = result.replace(f"{{{key}}}", value)

        return result.replace("{{", "{").replace("}}", "}")

    def add_template(self, name: str, template: str) -> None:
        """Register or replace a template."""
        self._templates[name] = template

    def get_template(self, name: str) -> str | None:
        """Return a template by name."""
        return self._templates.get(name)

    def list_templates(self) -> list[str]:
        """Return all registered template names."""
        return list(self._templates.keys())
