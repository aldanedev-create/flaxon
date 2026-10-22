# Lesson 5: Authentication — sessions, argon2, and CSRF

The accounts module (`modules/accounts.py`) is where the security promises of the
course are kept. Three properties matter:

1. **Passwords are hashed with argon2** via `flaxon.security.password`. The
   plaintext never leaves `register_user`, is never logged, and is never stored.
2. **Errors are generic.** Login and registration share one message so the API
   never reveals whether a username exists.
3. **Mutations are CSRF-protected and rate limited.**

```python
@accounts.post("/register")
async def register_user(request, ctx: AppContext):
    await ctx.guard(request, "register", REGISTER_LIMIT)
    payload = await json_body(request)
    user = await auth_service.register_user(username, email, password)
    auth_service.login_session(request, user)     # signed-cookie session
    return {"user": user.to_public()}
```

Authentication is a signed session cookie, exposed as `request.session`. Sessions
are set on register/login and cleared on logout:

```python
def login_session(request, user):
    request.session[SESSION_KEY] = user.id
```

The dangerous operations carry `require_csrf(ctx, request)`, which calls
`ctx.csrf.validate_request` and raises `403 Forbidden` on a missing or invalid
token. The browser fetches a token from `/api/auth/csrf-token` on startup and
echoes it on every mutation — the SPA's `api.ts` does this automatically.

**Checkpoint:** register a user, then call `/api/auth/me` *without* the session
cookie and confirm it returns `401`. Call `POST /api/servers/` with no CSRF
header and confirm `403`. Register with a 3-character password and confirm `400`
with the stable code `password_too_short`. These three responses are the
boundaries the rest of the course relies on.
