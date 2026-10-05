from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule

intelligence_module = FlaxonModule("guardian-intelligence")
intelligence_module.requires("guardian_state")


@intelligence_module.get("/api/intelligence/summary")
async def summary(state):
    return JSONResponse(state.summary())


@intelligence_module.get("/api/intelligence/graph")
async def graph(state):
    return JSONResponse(state.graph())
