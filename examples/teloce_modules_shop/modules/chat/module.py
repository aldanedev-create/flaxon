from pathlib import Path

from flaxon import WebSocket
from flaxon.modules import FlaxonModule


chat = FlaxonModule("chat", ui_dir=Path(__file__).parent / "ui")


@chat.websocket("/ws")
async def team_chat(socket: WebSocket):
    await socket.accept()
    while True:
        message = await socket.receive_json()
        await socket.send_json({"author": "Store Manager", "text": str(message.get("text", ""))})
