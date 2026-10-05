from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule

ring_module = FlaxonModule("guardian-ring")
ring_module.requires("guardian_state", "ring_simulator")


@ring_module.post("/api/demo/<scenario>")
async def demo(scenario: str, state, ring_simulator):
    await ring_simulator.run(scenario, state.ingest)
    return JSONResponse({"ok": True, "scenario": scenario, "summary": state.summary()})


@ring_module.post("/api/ring/events")
async def ingest(request, state):
    return JSONResponse(await state.ingest(await request.json()))
