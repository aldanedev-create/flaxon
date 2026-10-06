# Lesson 1: Understand the page lifecycle

Create the quick-start files and run the development server. `app.use_teloce()`
registers the UI tree and startup build. `request.compile()` returns an HTML
shell referencing the built component and styles. The browser mounts the
component, then its `mounted()` callback requests `/api/tasks`.

The template source is not simply returned as an HTML page. The integration is
client rendering: the initial body contains a mount point rather than rendered
task rows. If a page needs server-rendered HTML, use Flaxon's Jinax integration
and `request.render()`. Choose rendering according to the page's requirements.

Keep browser-only UI behavior inside components and privileged business work
inside Python endpoints. Context passed to `compile()` is serialized into the
page: it is suitable for public display values, never credentials.

**Checkpoint:** inspect page source and Network tools. Find the mount point,
compiled `.js`, stylesheet and API request. Disable JavaScript to understand
which content depends on the browser runtime.


## A complete app you can run

Use [Taskboard](../../examples/teloce_taskboard/README.md) as the working baseline.
The Python file below is complete. It contains a GET endpoint, validated POST
endpoint and page route. Keep the interface in `ui/`; Python should not contain
large HTML strings.

### `examples/teloce_taskboard/app.py`

```python
"""Taskboard teaching fixture: a Python API and a typed Teloce interface."""
from pathlib import Path

from flaxon import Flaxon, Request
from flaxon.http import JSONResponse
from flaxon.validation import Schema, fields

project_root = Path(__file__).resolve().parent
app = Flaxon("Taskboard", debug=True)
app.use_teloce(project_root=project_root, ui_dir="ui", title="Taskboard")

# This data resets when the process restarts. Lesson 8 explains persistence.
tasks = [{"id": 1, "title": "Read the full-stack lessons", "complete": False}]

class CreateTask(Schema):
    title = fields.StrField(required=True, min_length=1, max_length=200)

@app.get("/api/tasks")
async def list_tasks():
    return {"items": tasks}

@app.post("/api/tasks")
async def create_task(data: CreateTask):
    title = data.to_dict()["title"].strip()
    if not title:
        return JSONResponse({"error": "Enter a task title."}, status_code=422)

    task = {"id": len(tasks) + 1, "title": title, "complete": False}
    tasks.append(task)
    return JSONResponse(task, status_code=201)

@app.get("/")
async def home(request: Request):
    return await request.compile("app.html")
```

`CreateTask` is the request schema. Flaxon validates the JSON body before calling
the handler. `JSONResponse` lets the handler choose a status code. The page route
only selects a component; its browser-side API helper loads the tasks.

Run the example with `flaxon run app:app --reload` from its folder. A restart
resets this teaching fixture's in-memory tasks. Do not call it persistent storage.


[Course contents](index.md) · [Next lesson](02-components.md)
