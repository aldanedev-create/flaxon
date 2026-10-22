# Lesson 4: App context and dependency injection

Modules should not build the collaborators they need — they should *declare*
them and receive them. That is the job of `examples/discord_clone/context.py`
and Flaxon's container.

`AppContext` wraps verified Flaxon primitives: the CSRF protector, the rate
limiter, a broadcaster, and the realtime hub. It is constructed once and shared
by every request:

```python
class AppContext:
    def __init__(self, *, secret_key, broadcaster=None):
        self.csrf = CSRF(secret_key=secret_key)
        self.broadcaster = broadcaster or MemoryBroadcaster()
        self.hub = ChannelHub(self.broadcaster)
        self._limiters = {}

    async def guard(self, request, bucket, limit):
        if limit is None or not self.rate_limit_enabled:
            return
        if not await self._limiter(bucket, limit).check(request.scope):
            raise TooManyRequests("Too many requests — slow down and retry later")
```

`app.py` registers the instance under the key `"ctx"`. A module declares the
dependency and receives it as a route parameter:

```python
servers = FlaxonModule("servers")
servers.requires("ctx")                       # fail loudly at startup if missing

@servers.post("")
async def create_server(request, ctx: AppContext):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    ...
```

This is the discipline that keeps the project organized as it grows: mounting a
module on an app that forgot to build a context raises at startup, not on the
first request. The `ctx` parameter is injected by Flaxon's container, so route
handlers stay free of construction code.

**Checkpoint:** read `modules/_common.py`. Every mutating route funnels through
`require_csrf`, `json_body`, `authorize_server`, and `authorize_channel`. When
you add a new endpoint, it should reuse these helpers rather than re-implement
authorization — that is what "use Flaxon modules to organize" means in practice.
