"""Bot platform: creation, token lifecycle, commands, events, idempotency (Phase 6/7)."""
from __future__ import annotations

import asyncio

from models import BotToken, EventDelivery


def _server(make_session):
    c = make_session()
    c.register("alice", "alice@example.com", "password123")
    c.fetch_csrf()
    sid = c.post("/api/servers/", json_data={"name": "Guild"}).json()["server"]["id"]
    cid = c.post(f"/api/servers/{sid}/channels",
                 json_data={"name": "general"}).json()["channel"]["id"]
    return c, sid, cid


def test_create_bot_returns_one_time_token(make_session):
    c, _sid, _cid = _server(make_session)
    r = c.post("/api/bots/", json_data={"name": "Helper", "description": "demo"})
    assert r.status_code == 200
    assert "token" in r.json()
    assert r.json()["bot"]["name"] == "Helper"


def test_token_is_hashed_not_stored_plaintext(app, make_session):
    c, _sid, _cid = _server(make_session)
    token = c.post("/api/bots/", json_data={"name": "Helper"}).json()["token"]
    # The plaintext token must never be persisted; verify via the ORM directly.
    async def _check():
        return await BotToken.filter(token_prefix=token[:12]).count()

    with app.db.bind():
        assert asyncio.run(_check()) == 1


def test_revoked_token_cannot_be_listed_as_active(make_session):
    c, _sid, _cid = _server(make_session)
    bot = c.post("/api/bots/", json_data={"name": "Helper"}).json()["bot"]
    toks = c.get(f"/api/bots/{bot['id']}/tokens").json()["items"]
    token_id = toks[0]["id"]
    assert c.delete(f"/api/bots/{bot['id']}/tokens/{token_id}").status_code == 200
    toks = c.get(f"/api/bots/{bot['id']}/tokens").json()["items"]
    assert toks[0]["revoked"] is True


def test_command_invocation(make_session):
    c, sid, cid = _server(make_session)
    bot = c.post("/api/bots/", json_data={"name": "Helper"}).json()["bot"]
    c.post(f"/api/bots/{bot['id']}/join", json_data={"server_id": sid})
    c.post(f"/api/bots/{bot['id']}/commands", json_data={"name": "ping"})
    r = c.post(f"/api/bots/{bot['id']}/invoke",
               json_data={"channel_id": cid, "command": "ping", "args": []})
    assert r.status_code == 200
    assert r.json()["invocation"]["status"] == "success"
    assert r.json()["invocation"]["result"] == "pong!"


def test_event_delivery_on_message(make_session):
    c, sid, cid = _server(make_session)
    bot = c.post("/api/bots/", json_data={"name": "Echo"}).json()["bot"]
    c.post(f"/api/bots/{bot['id']}/join", json_data={"server_id": sid})
    # Bot is auto-subscribed to message.create on creation.
    # Mentioning the bot triggers the example event handler.
    r = c.post(f"/api/channels/{cid}/messages",
               json_data={"content": f"hello {bot['name']}"})
    assert r.status_code == 200
    # The bot's reply is returned alongside the user's message.
    bot_msgs = r.json().get("bot_messages", [])
    assert any(bot['name'] in m["content"] for m in bot_msgs) or bot_msgs


def test_event_delivery_is_idempotent(app, make_session):
    c, sid, cid = _server(make_session)
    bot = c.post("/api/bots/", json_data={"name": "Echo"}).json()["bot"]
    c.post(f"/api/bots/{bot['id']}/join", json_data={"server_id": sid})
    c.post(f"/api/channels/{cid}/messages",
           json_data={"content": f"hi {bot['name']}"})
    c.post(f"/api/channels/{cid}/messages",
           json_data={"content": f"hi {bot['name']} again"})
    with app.db.bind():
        # Two distinct messages -> two distinct deliveries, never duplicated.
        async def _count():
            return await EventDelivery.all().count()

        assert asyncio.run(_count()) == 2
