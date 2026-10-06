# Lesson 3: Connect writes to validated Python endpoints

The browser should send a small JSON payload; the server should decide whether
it is acceptable. For the teaching fixture, use an in-memory list:

```python
from flaxon.http import JSONResponse

items = []

@app.post("/api/tasks")
async def create_task(request: Request):
    try:
        data = await request.json()
    except ValueError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    title = data.get("title") if isinstance(data, dict) else None
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
        return JSONResponse({"error": "Title must contain 1–200 characters"}, status_code=422)
    task = {"id": len(items) + 1, "title": title.strip()}
    items.append(task)
    return JSONResponse(task, status_code=201)
```

Update the GET endpoint to return `items`. In the component, POST with
`Content-Type: application/json`, check `response.ok`, display the error and
clear the input only after success. Disable repeated submission while waiting.
In-memory IDs and storage are teaching fixtures and unsuitable for concurrent
production workers.

Use Flaxon's [validation guide](../guides/validation.md) for reusable schemas.
Client validation improves usability; server validation protects the API.
**Checkpoint:** submit an empty title, malformed JSON and a valid title. Check
status codes and verify that failed submissions leave the user's input intact.


## Put the browser contract in `.ts` files

Name your payloads instead of scattering anonymous objects through components.
These browser types describe expected data; the server schema still validates
actual requests.

### `examples/teloce_taskboard/ui/types.ts`

```ts
export interface Task {
  id: number;
  title: string;
  complete: boolean;
}

export interface TaskList {
  items: Task[];
}
```
### `examples/teloce_taskboard/ui/api.ts`

```ts
import type { Task, TaskList } from "./types.ts";

export async function loadTasks(): Promise<Task[]> {
  const response = await fetch("/api/tasks");

  if (!response.ok) {
    throw new Error("Could not load tasks. Try again.");
  }

  const payload: TaskList = await response.json();
  return payload.items;
}

export async function createTask(title: string): Promise<Task> {
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error("Could not save the task. Check its title and try again.");
  }

  return await response.json();
}
```

The helper checks HTTP status before reading success data. Catch its failure in
the component, keep the input intact, and show a message the user can act on.
The teaching helper checks status but does not validate arbitrary response JSON
at runtime. Add structural checks at an untrusted integration boundary.

For edits, use PATCH/PUT handlers; for deletion, use DELETE. The server must check
record ownership before either operation. Query parameters and typed path
parameters belong in route declarations; cookies, form uploads and headers are
available through `Request`. Refer to the request/response guides for signatures
rather than borrowing another framework's parameter names.


[Course contents](index.md) · [Previous lesson](02-components.md) · [Next lesson](04-typescript.md)
