"""Full happy-path journey: the entire stack working together end to end.

Walks one user from sign-up through the bot platform, touching auth, servers,
channels, messages, the bot API and logout — the same path the tutorial's final
lesson drives through the SPA.
"""
from __future__ import annotations


def test_full_user_journey(make_session):
    c = make_session()

    # 1. Register and confirm the session authenticates subsequent requests.
    assert c.register("journey", "journey@example.com", "password123").status_code == 200
    assert c.get("/api/auth/me").json()["user"]["username"] == "journey"
    c.fetch_csrf()

    # 2. Create a server; the owner auto-receives a #general channel.
    sid = c.post("/api/servers/", json_data={"name": "Journey Guild"}).json()["server"]["id"]
    cid = c.get(f"/api/servers/{sid}/channels").json()["items"][0]["id"]

    # 3. Send a message and read it back from durable history.
    mid = c.post(
        f"/api/channels/{cid}/messages", json_data={"content": "hello world"}
    ).json()["message"]["id"]
    items = c.get(f"/api/channels/{cid}/messages").json()["items"]
    assert items[0]["id"] == mid
    assert items[0]["content"] == "hello world"

    # 4. Stand up a bot, add it to the server, register /ping, and invoke it.
    bot = c.post("/api/bots/", json_data={"name": "Helper"}).json()["bot"]
    assert c.post(f"/api/bots/{bot['id']}/join", json_data={"server_id": sid}).status_code == 200
    assert c.post(f"/api/bots/{bot['id']}/commands", json_data={"name": "ping"}).status_code == 200
    r = c.post(
        f"/api/bots/{bot['id']}/invoke",
        json_data={"channel_id": cid, "command": "ping", "args": []},
    )
    assert r.json()["invocation"]["status"] == "success"
    assert r.json()["invocation"]["result"] == "pong!"

    # 5. Logging out ends the session.
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401
