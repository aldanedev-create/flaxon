
# WebSockets

## Overview

Flaxon provides built-in WebSocket support with:

- Real-time communication
- Room-based broadcasting
- Authentication
- Heartbeat detection
- Event handling
- Connection management

---

# Basic WebSocket

```python
from flaxon import WebSocket, WebSocketDisconnect


@app.websocket("/ws/echo")
async def echo(socket: WebSocket):

    await socket.accept()

    try:

        async for message in socket.iter_json():

            await socket.send_json({
                "echo": message
            })

    except WebSocketDisconnect:
        pass
````

---

# Room-Based Broadcasting

Clients can join rooms and broadcast messages to other connected clients.

```python
@app.websocket("/ws/chat/<room_id>")
async def chat(
    socket: WebSocket,
    room_id: str
):

    await socket.accept()

    await socket.join(room_id)


    try:

        async for message in socket.iter_json():

            await socket.broadcast_json(
                room_id,
                {
                    "room": room_id,
                    "message": message,
                    "sender": id(socket),
                }
            )

    finally:

        await socket.leave(room_id)
```

---

# Authentication

WebSockets can use the same authentication system as HTTP routes.

```python
from flaxon.security import (
    login_required,
    get_current_user,
)


@app.websocket("/ws/auth")
@login_required
async def auth_websocket(
    socket: WebSocket
):

    user = get_current_user(
        socket.scope
    )


    await socket.accept()


    await socket.send_json({
        "user": user.to_dict()
    })
```

---

# Heartbeat

Heartbeat detection automatically removes inactive connections.

```python
from flaxon.websocket import Heartbeat


heartbeat = Heartbeat(
    interval=30,
    timeout=60
)



@app.websocket("/ws/heartbeat")
async def heartbeat_ws(
    socket: WebSocket
):

    await socket.accept()


    await heartbeat.start(socket)


    try:

        async for message in socket.iter_json():

            # Handle messages

            pass


    finally:

        await heartbeat.stop(socket)
```

---

# Multiple Rooms

A single client can join multiple rooms.

```python
@app.websocket("/ws/multi")
async def multi_room(
    socket: WebSocket
):

    await socket.accept()


    await socket.join(
        "global"
    )


    await socket.join(
        "user-123"
    )


    async for message in socket.iter_json():

        room = message.get(
            "room"
        )


        if room:

            await socket.broadcast_json(
                room,
                message
            )
```

---

# WebSocket Events

Flaxon supports event-based WebSocket handlers.

```python
from flaxon.websocket import WebSocketEvents


@app.websocket("/ws/events")
async def events(
    socket: WebSocket
):

    ws_events = WebSocketEvents(
        socket
    )


    @ws_events.on_connect
    async def on_connect():

        print(
            "Client connected"
        )


    @ws_events.on_message
    async def on_message(data):

        await socket.send_json({
            "echo": data
        })


    @ws_events.on_disconnect
    async def on_disconnect(code):

        print(
            f"Client disconnected: {code}"
        )


    await ws_events.run()
```

---

# Broadcasting To All Clients

```python
@app.websocket("/ws/broadcast")
async def broadcast(
    socket: WebSocket
):

    await socket.accept()


    await socket.join(
        "all"
    )


    async for message in socket.iter_json():

        await socket.broadcast_json(
            "all",
            {
                "sender": id(socket),
                "message": message,
            }
        )
```

---

# Error Handling

```python
@app.websocket("/ws/error")
async def error_ws(
    socket: WebSocket
):

    try:

        await socket.accept()


        async for message in socket.iter_json():

            try:

                # Process message

                pass


            except ValueError as exc:

                await socket.send_json({
                    "error": str(exc)
                })


    except Exception:

        await socket.close(
            code=1011,
            reason="Internal error"
        )
```

---

# Complete Chat Example

```python
from flaxon import (
    Flaxon,
    WebSocket,
    WebSocketDisconnect,
)

from flaxon.websocket import Heartbeat


app = Flaxon(
    "chat-demo"
)


heartbeat = Heartbeat(
    interval=30,
    timeout=60
)


active_users = {}



@app.websocket("/ws/chat/<room_id>")
async def chat(
    socket: WebSocket,
    room_id: str
):

    user_id = str(
        id(socket)
    )


    await socket.accept()


    await socket.join(
        room_id
    )


    active_users[user_id] = {
        "room": room_id,
        "socket": socket,
    }


    await heartbeat.start(
        socket
    )


    await socket.broadcast_json(
        room_id,
        {
            "type": "user_joined",
            "user_id": user_id,
        }
    )


    try:

        async for message in socket.iter_json():

            await socket.broadcast_json(
                room_id,
                {
                    "type": "message",
                    "user_id": user_id,
                    "data": message,
                    "room": room_id,
                }
            )


    except WebSocketDisconnect:

        pass


    finally:

        await socket.leave(
            room_id
        )


        active_users.pop(
            user_id,
            None
        )


        await heartbeat.stop(
            socket
        )


        await socket.broadcast_json(
            room_id,
            {
                "type": "user_left",
                "user_id": user_id,
            }
        )



@app.get("/ws/stats")
async def ws_stats():

    return {

        "active_users": len(
            active_users
        ),

        "rooms": list(
            {
                user["room"]
                for user in active_users.values()
            }
        ),
    }
```

---

# WebSocket Best Practices

* Authenticate WebSocket connections.
* Use heartbeat monitoring.
* Handle disconnects gracefully.
* Validate incoming messages.
* Limit message size.
* Use rooms for large applications.
* Implement reconnection logic.
* Track active connections.
* Close unused connections.
* Use secure WebSockets (`wss://`) in production.

---

# Next Steps

Continue with:

* Push Notifications
* Background Tasks
* Mobile Backend
* Security
* Performance Optimization


## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.

## Production checklist

**Install a WebSocket implementation.** Plain Uvicorn cannot serve WebSockets: every handshake gets
HTTP 404. `pip install "flaxon[standard]"` includes `websockets`; with your own requirements, add
`websockets` or use `uvicorn[standard]`.

**Check the Origin if sockets use cookies or sessions.** Browsers do not apply the same-origin policy
to WebSockets, so any web page can open a socket to your server with the visitor's cookies attached
(cross-site WebSocket hijacking).

```python
from flaxon.websocket import WebSocketOriginMiddleware

app.add_middleware(WebSocketOriginMiddleware, allowed_origins=["https://app.example.com"])
```

Pages served from your own host are allowed automatically, `allow_missing_origin` (default `True`)
admits non-browser clients that send no `Origin`, and a refused handshake gets HTTP 403. Pair it
with `TrustedHostsMiddleware`.

**Tokens expire.** `WebSocketAuth` rejects expired tokens, tokens without a numeric `exp`, and
tokens with a bad signature. Browsers cannot set headers on a WebSocket, so a `?token=` query
parameter is accepted by default; URLs end up in logs, so keep those tokens short-lived or pass
`allow_query_token=False` if your clients can send an `Authorization` header.

**Know the close codes.** Clients can react to why a connection ended:

| Code | Meaning |
| --- | --- |
| 1003 | Binary frame where text was expected |
| 1007 | Invalid JSON |
| 1008 | Origin not allowed (sent before the handshake, so the client sees HTTP 403) |
| 1011 | Unhandled error in your handler (logged server-side, details never sent) |
| 1013 | Too slow to keep up (dropped from a broadcast) |
| 4000 + HTTP status | An `HTTPException` raised in the handler: 4401 unauthorized, 4403 forbidden |
| 4408 | Heartbeat timeout |

**Broadcasts are isolated.** A dead or slow client never affects the others: sends run
concurrently, a client that fails or takes longer than `send_timeout` (default 10 s) is dropped, and
connections are always removed from the manager and its rooms when a handler ends, however it ends.

**Limit connections.** `app.websocket_manager.max_connections = 10_000` refuses new handshakes when
full. Message size and protocol pings are server settings, for example
`uvicorn --ws-max-size 1048576 --ws-ping-interval 20 --ws-ping-timeout 20`. Behind nginx, forward the
`Upgrade` and `Connection` headers and raise `proxy_read_timeout`.

**Several workers need a broadcaster.** Each process has its own connections. Configure Redis once at
startup so rooms span workers:

```python
from flaxon.websocket.redis_backend import RedisBroadcaster

await app.websocket_manager.configure_broadcaster(RedisBroadcaster("redis://localhost:6379/0"))
```

Local clients get a message immediately and other workers deliver it to theirs, once. Rooms joined
later are subscribed automatically, a lost Redis connection is re-established with backoff, and an
outage never crashes the sender. Delivery is at-most-once: messages sent while Redis is unreachable
are not replayed. Channels are prefixed with `flaxon:ws:` (change it with `prefix=`). Deploy all
workers together when upgrading, because messages now carry an origin marker.

**Shutdown is graceful.** On shutdown every open connection is closed with 1001 so clients can
reconnect, and broadcaster resources are released.

**Heartbeats.** `Heartbeat` sends the text `"ping"` and expects the text `"pong"`; replies are recorded
for you and never reach your `receive` loop. Clients should answer pings and treat close code 4408 as
a reason to reconnect.
