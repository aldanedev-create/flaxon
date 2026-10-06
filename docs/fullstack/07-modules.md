# Lesson 7: Organize full-stack features with modules

Group tasks with their endpoints and UI rather than splitting the entire
project into unrelated frontend/backend repositories:

```python
from flaxon.modules import FlaxonModule

tasks = FlaxonModule("tasks", ui_dir=project_root / "modules/tasks/ui")

@tasks.get("/tasks")
async def list_tasks():
    return {"items": []}

app.mount_module(tasks, prefix="/api")
```

Mounting registers backend routes and the module's UI source. Directories must
remain inside the configured project root. Module names and UI roots must be
unique. A backend prefix does not automatically change browser page routes;
use `ui_routes` when a client route requires an explicit mapping.

Keep repository/data services separate from request handlers so a module can
be tested with a fixture service. Share a small design-system component library
instead of copying markup into every feature. Register sources before serving
traffic; concurrent runtime builds are not a deployment lifecycle.

**Checkpoint:** add a second module and verify both backend endpoints and browser
pages work. Deliberately introduce a duplicate client route and confirm the
build rejects it. See the [modules shop](../../examples/teloce_modules_shop).


## A module can own typed browser code

A useful feature layout is:

- `modules/tasks/routes.py`: HTTP boundary and module declaration.
- `modules/tasks/service.py`: business rules shared by endpoints and workers.
- `modules/tasks/ui/pages/Tasks.html`: feature page with `lang="ts"`.
- `modules/tasks/ui/api.ts`: typed browser request helpers.
- `modules/tasks/ui/types.ts`: browser-visible payload contracts.
- `modules/tasks/ui/components/TaskRow.html`: reusable feature component.

The browser API URL must match the Python mount prefix. A `/api/tasks` backend
prefix and `/tasks` browser page can coexist, but one does not automatically
configure the other. Keep page-to-service communication through endpoints.

Use `Router`/`include_router()` for API route composition without UI sources;
use `FlaxonModule` when a feature also contributes interface files and installers.
ASGI mounting is another boundary: it embeds a separate ASGI app, rather than
registering that app's UI files as Teloce sources. See the module and application
references for lifecycle and prefix behavior.


[Course contents](index.md) · [Previous lesson](06-routing.md) · [Next lesson](08-data-and-security.md)
