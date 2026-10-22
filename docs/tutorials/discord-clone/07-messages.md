# Lesson 7: Messages — durable history first

Messages are persisted *before* they are broadcast. This single rule is the
backbone of the whole realtime design: a client that misses a WebSocket event
can always recover the full history over HTTP. The message module is tiny
because the hard part (persistence, authorization) lives elsewhere:

```python
@messages.post("/<channel_id>/messages")
async def create(request, ctx: AppContext, channel_id):
    await ctx.guard(request, "msg", MESSAGE_CREATE_LIMIT)
    user = await auth_service.require_user(request)
    channel, server_id = await _channel_and_server(int(channel_id), user.id)
    message = await create_message(cid, author_id=user.id, content=content)
    await ctx.hub.broadcast(cid, {"type": "message.create", ...})   # live only
    produced = await dispatch_message_event(message, server_id, hub=ctx.hub)
    return {"message": message.to_public(), "bot_messages": [...]}
```

History is paginated with a cursor so the client can page backwards efficiently:

```python
@messages.get("/<channel_id>/messages")
async def history(request, channel_id):
    before_id = int(before) if before and before.isdigit() else None
    limit_i = ...  # clamped to MAX_HISTORY_LIMIT
    rows = await channel_history(cid, before_id=before_id, limit=limit_i or 50)
    return {"items": rows}
```

Deletion is authorized: the author may always delete; a server owner may delete
anything. Validation rejects empty and over-long content (`400`).

**Checkpoint:** send a message, read history, and confirm the new message is the
most recent. Send a second message and page back using the oldest id as the
`before` cursor — confirm you get the earlier page. Send a blank message and
confirm `400`; confirm a non-member is refused (`403`).
