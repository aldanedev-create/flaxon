# Lesson 10: The realtime hub and broadcaster

Live updates sit *on top of* durable history. The hub
(`services/hub.py`) tracks, per process, which local WebSocket connections
belong to which channel, and keeps ephemeral presence and typing state. It never
stores messages — it only forwards live traffic.

A browser opens one socket and subscribes to the channel it is viewing. The
WebSocket endpoint authorizes every subscribe against the database, so a socket
can never receive a channel its user is not a member of:

```python
@realtime.websocket("/ws")
async def ws(socket, ctx: AppContext):
    user_id = _ws_user_id(socket, ctx.secret_key)   # decode signed session cookie
    if user_id is None:
        await socket.close(code=4401); return
    await socket.accept()
    ...
    if ptype == "subscribe":
        channel = await Channel.get_or_none(id=cid)
        await authorize_channel(user_id, channel)     # enforced every time
        await ctx.hub.attach(socket, cid, user_id)
```

The hub publishes events to the broadcaster and listens for inbound events to
deliver to local sockets:

```python
async def broadcast(self, channel_id, event):
    await self.broadcaster.publish(str(channel_id), event)

async def _listen(self, channel_id):
    async for message in self.broadcaster.subscribe(str(channel_id)):
        await self._deliver_local(channel_id, message)   # to local sockets only
```

**Checkpoint:** connect two browser tabs to the same channel. Send a message in
one and confirm it appears in the other via the socket. Disconnect and reconnect
one tab; on reconnect it should re-subscribe and re-fetch canonical history from
`GET /channels/<id>/messages`. The socket is a notification, not the source of
truth.
