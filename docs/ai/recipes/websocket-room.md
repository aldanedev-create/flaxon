# Recipe: a WebSocket chat room

Serve WebSockets with `flaxon[standard]` and validate `Origin` on cookie-auth
sockets. Clients join a room and broadcast JSON to it.

```python
from flaxon import Flaxon
from flaxon.websocket import WebSocket, WebSocketOriginMiddleware

app = Flaxon("chat-recipe")
app.add_middleware(
    WebSocketOriginMiddleware,
    allowed_origins=["https://app.example.com"],
)


@app.websocket("/ws/chat/<room_id>")
async def chat(socket: WebSocket, room_id: str):
    await socket.accept()
    await socket.join(room_id)
    try:
        async for message in socket.iter_json():
            await socket.broadcast_json(room_id, {"room": room_id, "message": message})
    finally:
        await socket.leave(room_id)
```

Routes use `<int:id>`-style converters (not `{id}`). Bad origins are rejected
before the handshake completes with close code 1008 (HTTP 403 to browsers).
