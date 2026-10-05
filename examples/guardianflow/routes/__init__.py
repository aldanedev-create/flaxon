from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule

pages = FlaxonModule("guardian-pages")
pages.requires("guardian_state")


@pages.get("/")
@pages.get("/dashboard")
async def dashboard(request, state):
    return await request.render("dashboard.jinja", {
        "active": "dashboard", "summary": state.summary(),
        "events": list(state.events)[-8:][::-1], "alerts": state.alerts[:5],
        "graph": state.graph(), "cameras": list(state.cameras.values()),
    })


@pages.get("/events")
async def events_page(request, state):
    return await request.render("events.jinja", {"active": "events", "events": list(state.events)[::-1]})


@pages.get("/cameras")
async def cameras_page(request, state):
    return await request.render("cameras.jinja", {"active": "cameras", "cameras": list(state.cameras.values())})


@pages.get("/alerts")
async def alerts_page(request, state):
    return await request.render("alerts.jinja", {"active": "alerts", "alerts": state.alerts})


@pages.get("/rules")
async def rules_page(request, state):
    return await request.render("rules.jinja", {"active": "rules", "rules": list(state.policies.rules.values())})


@pages.get("/api/events")
async def events_api(state):
    return JSONResponse([event.to_dict() for event in reversed(state.events)])


@pages.get("/api/alerts")
async def alerts_api(state):
    return JSONResponse([alert.to_dict() for alert in state.alerts])


@pages.post("/api/alerts/<alert_id>/<action>")
async def alert_action(alert_id: str, action: str, state):
    for alert in state.alerts:
        if alert.id == alert_id and action in {"review", "dismiss"}:
            alert.status = "reviewed" if action == "review" else "dismissed"
            return JSONResponse(alert.to_dict())
    return JSONResponse({"error": "alert not found"}, status_code=404)
