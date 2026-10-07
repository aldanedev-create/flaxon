# Lesson 9: Add live updates and test the full boundary

Use a Flaxon WebSocket endpoint for task changes when polling is insufficient.
Consult the [WebSocket guide](../guides/websockets.md) for its concrete API.
Authenticate the connection, authorize room membership and validate incoming
messages. A successful HTTP login does not automatically authorize every room.

The Teloce component opens the socket after mounting and closes it in
`beforeUnmount()`. Show disconnected state, retry with bounded backoff, and
refetch canonical data after reconnecting. A broadcast is a notification;
the durable database remains the source of truth.

Use `TestClient` for endpoint behavior and a real browser for component behavior.
The head/TypeScript integration tests build the example and request generated
assets, but browser tests are still needed for library timing and interaction.
Test successful updates, rejected writes, unknown routes, escaping, empty lists
and offline states. Avoid asserting only that HTML returns 200.

**Checkpoint:** open two browser windows, update a task in one, disconnect and
reconnect the other, then navigate away and check that its old socket closes.
Use fixtures and deterministic waits rather than arbitrary long sleeps.


## A typed WebSocket helper

For an echo teaching route, the HTTP API and socket are independent boundaries:

```python
from flaxon import WebSocket, WebSocketDisconnect

@app.websocket("/ws/echo")
async def echo(socket: WebSocket):
    await socket.accept()
    try:
        async for message in socket.iter_json():
            await socket.send_json({"echo": message})
    except WebSocketDisconnect:
        pass
```

```ts
// ui/live.ts — import this helper from a component
export function connectEcho(onMessage: (message: string) => void): WebSocket {
  const protocol: string = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${location.host}/ws/echo`);

  socket.addEventListener("message", (event: MessageEvent) => {
    onMessage(String(event.data));
  });

  return socket;
}
```

Create the connection in `mounted()` and close it in `beforeUnmount()`. Register
open/error/close handlers to update state. This small helper demonstrates delivery;
it does not add authentication, reconnection or a task change protocol.

For shared browser state, Teloce's explicit signals expose `get`, `set`, `update`,
`peek` and `subscribe`. `createComputed` derives a value; `createEffect` returns an
effect with `stop()`. `subscribe` returns an unsubscribe function. Serve the actual
packaged runtime modules and dispose subscriptions when their owner unmounts.
Do not assume the signal API of another framework is identical.


[Course contents](index.md) · [Previous lesson](08-data-and-security.md) · [Next lesson](10-production.md)
