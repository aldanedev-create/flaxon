"""Flaxon Admin + CMS: the staff face of the course project.

Three things the course must demonstrate about the admin subsystem:

1. The admin UI is reachable (login page is served).
2. The dashboard is protected — an anonymous browser is bounced (permission
   separation between the public app and the staff console).
3. The CMS "announcement" content type is registered, and the admin auth
   service actually authenticates credentials.
"""
from __future__ import annotations

import asyncio


def test_admin_login_page_is_served(client):
    r = client.get("/admin/login")
    assert r.status_code == 200
    assert "login" in r.content.decode("utf-8", "replace").lower()


def test_admin_dashboard_is_protected(client):
    # No admin session -> the staff console refuses to render.
    r = client.get("/admin/")
    assert r.status_code in (302, 401)


def test_cms_registers_announcement_content_type(app):
    # The app wires an editorial "announcement" type into Flaxon CMS.
    assert "announcement" in app.cms.content_types


def test_admin_auth_authenticates_credentials(app):
    """Admin login works: valid credentials yield a session token; bad ones don't.

    Admin users live in the admin auth service; we register one in-process (the
    same way the `setup-admin` command persists via the admin store) and then
    exercise the login/verify logic directly.
    """
    auth = app._flaxon_admin_auth
    record = auth.add_user(
        {
            "username": "seedadmin",
            "password_hash": auth.hasher.hash("password123"),
            "roles": ["administrator"],
            "permissions": ["admin.superuser"],
        }
    )
    auth.store.mutate("users", "seedadmin", lambda value: {**value, **record}, default={})

    # A correct password produces a session token.
    token = asyncio.run(auth.login("seedadmin", "password123"))
    assert token is not None

    # Wrong password, and an unknown user, both fail closed.
    assert asyncio.run(_verify(auth, "seedadmin", "wrong")) is None
    assert asyncio.run(_verify(auth, "ghost", "password123")) is None


async def _verify(auth, username, password):
    return auth.verify(username, password)
