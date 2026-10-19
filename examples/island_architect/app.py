"""Island Architect — design a system for one island, then simulate it.

    python management.py makemigrations
    python management.py migrate
    python management.py runserver        # http://127.0.0.1:8000

How the three pieces split:

  Flaxon    owns the data. One Tortoise table (`models.Design`) holds saved
            designs, and the JSON API below validates and serves them.
  Teloce    owns the interface. `ui/` is a single-page component tree that is
            compiled to browser JavaScript on first request.
  static/js owns the simulation. `sim.js` is plain JavaScript so the browser can
            step it tick by tick with no round trip — see the Learn tab.

The API is the whole contract between the two: the browser never touches the
database, and Python never renders HTML.
"""
from __future__ import annotations

from flaxon import Flaxon, Request
from flaxon.http import JSONResponse
from flaxon.validation import Schema, fields as vfields

from models import Design

MAX_NODES = 24
MAX_EDGES = 48
NODE_KINDS = {"client", "edge", "service", "cache", "queue", "db"}
SCENARIOS = {"calm-day", "peak-season", "storm", "cache-cold", "queue-backup"}


class DesignSchema(Schema):
    """Request body for creating or updating a design."""

    name = vfields.StrField(required=True, min_length=1, max_length=120)
    scenario = vfields.StrField(required=False, max_length=40)
    seed = vfields.IntField(required=False, minimum=0, maximum=999999)
    graph = vfields.AnyField(required=False)


def graph_problems(graph):
    """Structural checks that keep a stored design simulatable.

    The browser runs the same checks before it enables Save (see
    `validateDesign` in static/js/island.js); this is the server-side copy, so a
    hand-rolled curl call cannot store something the simulator cannot read.
    """
    problems = []
    if not isinstance(graph, dict):
        return ["graph must be an object with 'nodes' and 'edges'."]

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not nodes:
        problems.append("graph.nodes must be a non-empty array.")
        nodes = []
    if not isinstance(edges, list):
        problems.append("graph.edges must be an array.")
        edges = []
    if len(nodes) > MAX_NODES:
        problems.append(f"a design may hold at most {MAX_NODES} nodes.")
    if len(edges) > MAX_EDGES:
        problems.append(f"a design may hold at most {MAX_EDGES} edges.")

    node_ids = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            problems.append(f"node {index} must be an object.")
            continue
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            problems.append(f"node {index} needs an id.")
        elif node_id in node_ids:
            problems.append(f"duplicate node id '{node_id}'.")
        node_ids.add(node_id)
        if str(node.get("kind") or "") not in NODE_KINDS:
            problems.append(f"node '{node_id}' has an unknown kind '{node.get('kind')}'.")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            problems.append(f"edge {index} must be an object.")
            continue
        source = str(edge.get("from") or "")
        target = str(edge.get("to") or "")
        if source not in node_ids or target not in node_ids:
            problems.append(f"edge {index} points at a node that does not exist.")
    return problems


def design_summary(design):
    """List view: enough to pick a design, without shipping the whole graph."""
    nodes = (design.graph or {}).get("nodes") or []
    edges = (design.graph or {}).get("edges") or []
    return {
        "id": design.id,
        "name": design.name,
        "scenario": design.scenario,
        "seed": design.seed,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "updated_at": design.updated_at.isoformat() if design.updated_at else None,
    }


def design_record(design):
    record = design_summary(design)
    record["graph"] = design.graph or {"nodes": [], "edges": []}
    return record


def create_app():
    app = Flaxon.from_settings()
    settings = app.settings
    DATA_DIR = settings.root / "data"
    DATA_DIR.mkdir(exist_ok=True)

    # Teloce is configured before the management guard so `build` and `typecheck`
    # commands still work when the database is not reachable.
    app.use_teloce(
        project_root=settings.root,
        ui_dir="ui",
        title="Island Architect",
        description="Design a system for one island, then simulate it.",
    )

    if app.is_management:
        return app

    # ---------------------------------------------------------------- API
    # Registered before the SPA catch-all so /api/* never falls through to it.

    @app.get("/api/designs")
    async def list_designs():
        rows = await Design.all().order_by("-updated_at")
        return {"items": [design_summary(row) for row in rows]}

    @app.post("/api/designs")
    async def create_design(data: DesignSchema):
        payload = data.to_dict()
        graph = payload.get("graph") or {"nodes": [], "edges": []}
        problems = graph_problems(graph)
        if problems:
            return JSONResponse({"error": "Invalid design.", "problems": problems}, status_code=422)

        design = await Design.create(
            name=payload["name"],
            scenario=payload.get("scenario") or "calm-day",
            seed=payload.get("seed") if payload.get("seed") is not None else 7,
            graph=graph,
        )
        return JSONResponse(design_record(design), status_code=201)

    @app.get("/api/designs/<int:design_id>")
    async def get_design(request: Request, design_id: int):
        design = await Design.get_or_none(id=design_id)
        if design is None:
            return JSONResponse({"error": "Design not found."}, status_code=404)
        return design_record(design)

    @app.put("/api/designs/<int:design_id>")
    async def update_design(request: Request, design_id: int):
        design = await Design.get_or_none(id=design_id)
        if design is None:
            return JSONResponse({"error": "Design not found."}, status_code=404)

        body = await request.json() or {}
        try:
            payload = DesignSchema.load(body).to_dict()
        except Exception:
            return JSONResponse(
                {"error": "Invalid design body.", "problems": ["name is required (1-120 characters)."]},
                status_code=422,
            )

        graph = payload.get("graph")
        if graph is not None:
            problems = graph_problems(graph)
            if problems:
                return JSONResponse({"error": "Invalid design.", "problems": problems}, status_code=422)
            design.graph = graph
        if payload.get("scenario"):
            design.scenario = payload["scenario"]
        if payload.get("seed") is not None:
            design.seed = payload["seed"]
        design.name = payload["name"]
        await design.save()
        return design_record(design)

    @app.delete("/api/designs/<int:design_id>")
    async def delete_design(request: Request, design_id: int):
        design = await Design.get_or_none(id=design_id)
        if design is None:
            return JSONResponse({"error": "Design not found."}, status_code=404)
        await design.delete()
        return JSONResponse({"deleted": design_id}, status_code=200)

    @app.get("/api/scenarios")
    async def list_scenarios():
        """Server-side copy of the scenario ids so a client cannot invent one."""
        return {"items": sorted(SCENARIOS)}

    # ---------------------------------------------------------------- SPA
    @app.get("/")
    @app.get("/<path:spa_path>")
    async def spa(request: Request, spa_path: str = ""):
        return await request.compile("app.html", {"island": "Jamaica"})

    return app


app = create_app()
