"""Security controls: CSRF enforcement, authentication gates, isolation.

These tests pin down the promises the course makes about the boundary between
the browser (which can be tricked into cross-site requests) and the API.
"""
from __future__ import annotations


def _authed_owner(make_session):
    c = make_session()
    c.register("owner", "owner@example.com", "password123")
    # fetch_csrf() primes a valid token; the mutation tests then tamper with it.
    c.fetch_csrf()
    return c


def test_valid_csrf_allows_mutation(make_session):
    c = _authed_owner(make_session)
    r = c.post("/api/servers/", json_data={"name": "Guild"})
    assert r.status_code == 200


def test_invalid_csrf_is_rejected(make_session):
    c = _authed_owner(make_session)
    # Swap the primed token for garbage; CSRF validation must refuse it.
    c.csrf = "not-a-real-token"
    r = c.post("/api/servers/", json_data={"name": "Guild"})
    assert r.status_code == 403


def test_unauthenticated_mutation_requires_login(make_session):
    # No session cookie at all: the request must fail before any CSRF check.
    c = make_session()
    r = c.post("/api/servers/", json_data={"name": "Guild"})
    assert r.status_code == 401


def test_private_channel_hidden_from_unauthorized_member(make_session):
    """Isolation is enforced in the database, not only hidden in the UI.

    Mirrors the lesson that private channels rely on a ChannelAccess grant, so a
    server member without the grant is refused at the API layer.
    """
    owner = _authed_owner(make_session)
    sid = owner.post("/api/servers/", json_data={"name": "Guild"}).json()["server"]["id"]
    invite = owner.get(f"/api/servers/{sid}").json()["server"]["invite_code"]

    bob = make_session()
    bob.register("bob", "bob@example.com", "password123")
    bob.fetch_csrf()
    assert bob.post("/api/servers/join", json_data={"invite_code": invite}).status_code == 200

    priv = owner.post(
        f"/api/servers/{sid}/channels", json_data={"name": "secret", "is_private": True}
    ).json()["channel"]
    # bob is a member but holds no ChannelAccess grant -> 403 on the messages API.
    assert bob.get(f"/api/channels/{priv['id']}/messages").status_code == 403
    # The owner, who created the channel and auto-received a grant, can read it.
    assert owner.get(f"/api/channels/{priv['id']}/messages").status_code == 200
