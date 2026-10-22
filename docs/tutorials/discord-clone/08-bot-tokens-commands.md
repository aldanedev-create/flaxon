# Lesson 8: Bot platform — one-time tokens and slash commands

The bot platform lets users extend the app without running untrusted code in the
web process. A bot is owned by a user; creating one mints a token and subscribes
it to `message.create` so the example handler works out of the box:

```python
@bots.post("")
async def create_bot(request, ctx: AppContext):
    user = await auth_service.require_user(request)
    bot = await Bot.create(owner=user, name=name, description=description)
    await EventSubscription.create(bot=bot, event_type="message.create")
    raw, _token = await issue_token(bot, label="default")
    return {"bot": bot.to_public(), "token": raw}   # plaintext shown ONCE
```

`issue_token` stores only a SHA-256 hash plus a display prefix
(`services/tokens.py`) — the same one-way pattern you would use for any
credential. Tokens can be revoked, and a revoked token can no longer authenticate.

Slash commands are registered as database rows; the in-app invoke entry point
runs the matching handler:

```python
@bots.post("/<bot_id>/invoke")
async def invoke(request, ctx: AppContext, bot_id):
    command = await SlashCommand.get_or_none(bot_id=bot.id, name=name)
    invocation, produced = await execute_command(bot, command, ...)
    for m in produced:
        await ctx.hub.broadcast(channel_id, {"type": "message.create", ...})
    return {"invocation": {...}, "messages": [...]}
```

Handlers are plain registered functions in `services/bots.py`, e.g.
`@command("ping")` returning `"pong!"`. No arbitrary Python runs in the web
process — only the handlers the platform defines.

**Checkpoint:** create a bot, capture its token, register `/ping`, and invoke it
from the API. Confirm the invocation returns `status: "success"` and
`result: "pong!"`. Revoke the token and confirm a revoked token no longer
authenticates (the token list marks it `revoked: true`).
