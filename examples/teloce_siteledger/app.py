from pathlib import Path

from flaxon import Flaxon, Request


ROOT = Path(__file__).parent
app = Flaxon("SiteLedger", debug=True)
app.use_teloce(project_root=ROOT, ui_dir="ui", title="SiteLedger")

JOBS = [
    {"id": 1, "customer": "Harbour View Bakery", "status": "In progress", "total": 485000},
    {"id": 2, "customer": "Mona Family Home", "status": "Site visit", "total": 125000},
]


@app.get("/api/jobs")
async def jobs():
    return {"items": JOBS}


@app.get("/api/jobs/<job_id>")
async def job(job_id: str):
    return next((item for item in JOBS if str(item["id"]) == job_id), {"error": "Job not found"})


@app.get("/")
@app.get("/<path:spa_path>")
async def spa(request: Request, spa_path: str = ""):
    return await request.compile(
        "app.html",
        {"business": "Morgan Build & Repair", "currency": "JMD"},
    )
