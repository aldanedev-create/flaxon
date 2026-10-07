# Full-stack quick start

Build a Python API and a Teloce interface in the same project. Python 3.11+ is
required. Create a virtual environment and install compatible Flaxon/Teloce releases:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install "flaxon[standard]"
```

For unreleased repository features, install your local Flaxon and teloce-py
checkouts with `pip install -e /path/to/teloce-py -e '/path/to/flaxon[standard]'`.

Create `app.py`:

```python
from pathlib import Path
from flaxon import Flaxon, Request

app = Flaxon("Taskboard", debug=True)
app.use_teloce(project_root=Path(__file__).parent, ui_dir="ui", title="Taskboard")

@app.get("/api/tasks")
async def tasks():
    return {"items": [{"id": 1, "title": "Try Flaxon"}]}

@app.get("/")
async def home(request: Request):
    return await request.compile("app.html")
```

Create `ui/app.html`:

```html
<template>
  <main>
    <h1>Taskboard</h1>
    <p role="status">{{ status }}</p>
    <ul>
      <li v-for="task in tasks" :key="task.id">{{ task.title }}</li>
    </ul>
  </main>
</template>
<script>
export default {
  data() {
    return { tasks: [], status: "Loading…" };
  },
  async mounted() {
    try {
      const response = await fetch("/api/tasks");
      if (!response.ok) {
        throw new Error("Could not load tasks");
      }
      this.tasks = (await response.json()).items;
      this.status = "Ready";
    } catch {
      this.status = "Could not load tasks. Refresh to retry.";
    }
  }
};
</script>
<style scoped>main { max-width: 48rem; margin: auto; font-family: system-ui; }</style>
```

Run `flaxon run app:app --reload` and open http://127.0.0.1:8000.
The startup build turns the component into JavaScript. The returned HTML shell
mounts it, then the browser fetches the Python API. Changes trigger a server
restart; refresh the browser afterward. This is not browser HMR.

The fixture has no persistence or accounts. Continue with the
[10 full-stack lessons](fullstack/index.md) to add data, validation, modules,
authorization, testing and deployment. See the runnable
[TypeScript/CDN converter](../examples/teloce_head_ts/README.md) for `.vel` and `.ts`.
