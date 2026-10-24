"""Authentication and session integrity (covers Phase 5 security basics)."""
from __future__ import annotations


def test_register_then_me(client):
    r = client.register("alice", "alice@example.com", "password123")
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "alice"
    # The session cookie from registration authenticates later requests.
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "alice"


def test_login_roundtrip(client):
    client.register("bob", "bob@example.com", "password123")
    client.cookies.clear()  # forget the registered session
    r = client.login("bob", "password123")
    assert r.status_code == 200
    assert client.get("/api/auth/me").json()["user"]["username"] == "bob"


def test_wrong_password_does_not_reveal_account(client):
    client.register("carol", "carol@example.com", "password123")
    client.cookies.clear()
    r = client.login("carol", "wrong-password")
    # Generic error; must not say "wrong password" vs "no such user".
    assert r.status_code == 401
    assert "Invalid username or password" in r.json()["error"]["message"]


def test_duplicate_username_rejected(client):
    client.register("dave", "dave@example.com", "password123")
    r = client.register("dave", "other@example.com", "password123")
    assert r.status_code == 400


def test_short_password_rejected(client):
    r = client.register("eve", "eve@example.com", "short")
    assert r.status_code == 400


def test_unauthenticated_me_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client):
    client.register("frank", "frank@example.com", "password123")
    assert client.get("/api/auth/me").status_code == 200
    r = client.post("/api/auth/logout")  # CSRF-protected; client auto-adds token
    assert r.status_code == 200
    # A fresh client (no cookie) is now anonymous.
    assert client.get("/api/auth/me").status_code == 401


def test_profile_update(client):
    client.register("grace", "grace@example.com", "password123")
    client.fetch_csrf()
    r = client.patch("/api/auth/profile", json_data={"display_name": "Gracie"})
    assert r.status_code == 200
    assert r.json()["user"]["display_name"] == "Gracie"
