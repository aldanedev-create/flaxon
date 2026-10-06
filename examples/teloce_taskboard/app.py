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
