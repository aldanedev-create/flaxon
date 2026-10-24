"""Servers, channels, roles, members and authorization (Phase 5/6)."""
from __future__ import annotations


def _register(client, name):
    client.register(name, f"{name}@example.com", "password123")
    return client


def _owner_session(make_session):
    c = make_session()
    c.register("owner", "owner@example.com", "password123")
    c.fetch_csrf()
    sid = c.post("/api/servers/", json_data={"name": "Guild"}).json()["server"]["id"]
    return c, sid


def test_create_and_list_server(client):
    _register(client, "alice")
    client.fetch_csrf()
    r = client.post("/api/servers/", json_data={"name": "My Guild"})
    assert r.status_code == 200
    sid = r.json()["server"]["id"]

    r = client.get("/api/servers/")
    assert r.status_code == 200
    assert sid in [s["id"] for s in r.json()["items"]]


def test_get_server_returns_permissions(make_session):
    owner, sid = _owner_session(make_session)
    r = owner.get(f"/api/servers/{sid}")
    assert r.status_code == 200
    assert "Administrator" in r.json()["permissions"]  # owner is implied admin


def test_owner_sees_auto_channel(make_session):
    owner, sid = _owner_session(make_session)
    r = owner.get(f"/api/servers/{sid}/channels")
    assert r.status_code == 200
    assert "general" in [c["name"] for c in r.json()["items"]]


def test_member_cannot_create_channel_without_permission(make_session):
    owner, sid = _owner_session(make_session)
    invite = owner.get(f"/api/servers/{sid}").json()["server"]["invite_code"]

    bob = make_session()
    bob.register("bob", "bob@example.com", "password123")
    bob.fetch_csrf()
    assert bob.post("/api/servers/join", json_data={"invite_code": invite}).status_code == 200
    # Plain member lacks MANAGE_CHANNELS -> forbidden.
    assert bob.post(f"/api/servers/{sid}/channels",
                    json_data={"name": "rogue"}).status_code == 403


def test_private_channel_hidden_from_unauthorized_member(make_session):
    owner, sid = _owner_session(make_session)
    invite = owner.get(f"/api/servers/{sid}").json()["server"]["invite_code"]

    bob = make_session()
    bob.register("bob", "bob@example.com", "password123")
    bob.fetch_csrf()
    bob.post("/api/servers/join", json_data={"invite_code": invite})

    priv = owner.post(f"/api/servers/{sid}/channels",
                      json_data={"name": "secret", "is_private": True}).json()["channel"]
    owner_visible = [c["id"] for c in owner.get(f"/api/servers/{sid}/channels").json()["items"]]
    bob_visible = [c["id"] for c in bob.get(f"/api/servers/{sid}/channels").json()["items"]]
    assert priv["id"] in owner_visible
    assert priv["id"] not in bob_visible


def test_invite_join_and_member_list(make_session):
    owner, sid = _owner_session(make_session)
    invite = owner.get(f"/api/servers/{sid}").json()["server"]["invite_code"]

    bob = make_session()
    bob.register("bob", "bob@example.com", "password123")
    bob.fetch_csrf()
    assert bob.post("/api/servers/join", json_data={"invite_code": invite}).status_code == 200

    r = owner.get(f"/api/servers/{sid}/members")
    assert {m["user"]["username"] for m in r.json()["items"]} == {"owner", "bob"}


def test_create_role_and_assign(make_session):
    owner, sid = _owner_session(make_session)
    r = owner.post(f"/api/servers/{sid}/roles",
                   json_data={"name": "mod", "permissions": 8})
    assert r.status_code == 200
    role_id = r.json()["role"]["id"]

    bob = make_session()
    bob.register("bob", "bob@example.com", "password123")
    bob.fetch_csrf()
    invite = owner.get(f"/api/servers/{sid}").json()["server"]["invite_code"]
    bob.post("/api/servers/join", json_data={"invite_code": invite})
    assert owner.post(f"/api/servers/{sid}/members/bob/role",
                      json_data={"role_id": role_id}).status_code == 200
    roles = owner.get(f"/api/servers/{sid}/roles").json()["items"]
    assert any(rl["name"] == "mod" for rl in roles)
