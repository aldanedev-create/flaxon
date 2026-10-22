"""Registration, login, logout, and session introspection.

Mounted at ``/api/auth``. Security properties the course leans on:

- Passwords are hashed with Flaxon's argon2 hasher (``flaxon.security.password``);
  the plaintext never leaves this function and is never logged or stored.
- Login and registration are rate limited per client, so credential stuffing is
  expensive rather than free.
- Error messages are deliberately generic: we never reveal which half of a
  credential pair was wrong.
"""
from __future__ import annotations

from flaxon.exceptions import BadRequest, Unauthorized
from flaxon.modules import FlaxonModule

from context import AppContext
from modules._common import json_body, require_csrf
from services import auth as auth_service

accounts = FlaxonModule("accounts")
accounts.requires("ctx")

# Buckets are (max requests, window seconds).
LOGIN_LIMIT = (10, 60)
REGISTER_LIMIT = (5, 60)


@accounts.get("/csrf-token")
async def csrf_token(ctx: AppContext):
    """Issue a CSRF token the SPA echoes on every mutation."""
    return {"token": ctx.csrf.generate_token()}


@accounts.post("/register")
async def register_user(request, ctx: AppContext):
    await ctx.guard(request, "register", REGISTER_LIMIT)
    payload = await json_body(request)
    try:
        user = await auth_service.register_user(
            str(payload.get("username", "")).strip(),
            str(payload.get("email", "")).strip(),
            str(payload.get("password", "")),
        )
    except ValueError as exc:
        # Validation failures become a 400 with a stable, machine-readable code.
        raise BadRequest(str(exc))
    auth_service.login_session(request, user)
    return {"user": user.to_public()}


@accounts.post("/login")
async def login(request, ctx: AppContext):
    await ctx.guard(request, "login", LOGIN_LIMIT)
    payload = await json_body(request)
    user = await auth_service.authenticate(
        str(payload.get("username", "")).strip(), str(payload.get("password", ""))
    )
    if user is None:
        # One message for unknown user, wrong password and disabled account:
        # nothing here confirms that an account exists.
        raise Unauthorized("Invalid username or password")
    auth_service.login_session(request, user)
    return {"user": user.to_public()}


@accounts.post("/logout")
async def logout(request, ctx: AppContext):
    require_csrf(ctx, request)
    auth_service.logout_session(request)
    return {"ok": True}


@accounts.get("/me")
async def me(request):
    user = await auth_service.current_user(request)
    if user is None:
        raise Unauthorized("Not signed in")
    return {"user": user.to_public()}


@accounts.patch("/profile")
async def update_profile(request, ctx: AppContext):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    payload = await json_body(request)
    if payload.get("display_name") is not None:
        user.display_name = str(payload["display_name"])[:80]
        await user.save(update_fields=["display_name"])
    if payload.get("avatar_color") is not None:
        user.avatar_color = str(payload["avatar_color"])[:7]
        await user.save(update_fields=["avatar_color"])
    return {"user": user.to_public()}
