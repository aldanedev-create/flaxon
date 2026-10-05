from flaxon.modules import FlaxonModule

notifications_module = FlaxonModule("guardian-notifications")
notifications_module.requires("guardian_state")


@notifications_module.websocket("/ws/live")
async def live(socket, state):
    await socket.accept()
    await socket.join("guardianflow")
    await socket.send_json({"kind": "snapshot", "summary": state.summary(), "events": [event.to_dict() for event in state.events]})
    async for _message in socket.iter_json():
        pass
