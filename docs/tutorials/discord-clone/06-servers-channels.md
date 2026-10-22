# Lesson 6: Servers, channels, roles, and permissions

A server is the unit of community. Creating one makes the owner its first member
and seeds a `#general` channel. Membership is the gate for everything else:

```python
@servers.post("")
async def create_server(request, ctx: AppContext):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    server = await Server.create(name=name, owner=user, invite_code=_invoken())
    await Membership.create(server=server, user=user)          # owner is member #1
    await Channel.create(server=server, name="general", position=0)
    return {"server": _public(server)}
```

Permissions are a single bitmask on a role. The owner always has
`ADMINISTRATOR`; everyone else combines the `@everyone` baseline
(`VIEW_CHANNEL | SEND_MESSAGES`) with their assigned role:

```python
OWNER       -> ADMINISTRATOR
@everyone   -> VIEW_CHANNEL | SEND_MESSAGES   (DEFAULT_EVERYONE)
role "mod"  -> ORed on top of @everyone
```

`services/access.py` resolves a user's effective permissions, and
`modules/_common.py` enforces them:

```python
async def authorize_server(user_id, server_id, flag=None):
    if not await is_member(user_id, server_id):
        raise Forbidden("You are not a member of this server")
    if flag is not None:
        perms = await effective_permissions(user_id, server_id)
        if not (has_flag(perms, flag) or has_flag(perms, ADMINISTRATOR)):
            raise Forbidden("You do not have permission to do that")
```

**Private channels** are the lesson that authorization must live in the
database. A member without a `ChannelAccess` grant is refused at the API layer,
even though they are a server member — see `authorize_channel` in
`modules/_common.py`. The UI hides them too, but the DB is the authority.

**Checkpoint:** create a server, invite a second user, assign them a role with
`MANAGE_CHANNELS`, and confirm the owner can create a channel while the plain
member cannot (`403`). Create a private channel and confirm the plain member is
refused when listing its messages.
