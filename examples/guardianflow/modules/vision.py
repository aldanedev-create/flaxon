from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule

vision_module = FlaxonModule("guardian-vision")
vision_module.requires("guardian_state")


@vision_module.get("/api/vision/facts")
async def facts(state):
    return JSONResponse([fact.to_dict() for fact in state.facts])
