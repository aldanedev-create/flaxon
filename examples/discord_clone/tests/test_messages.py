"""Message history, creation, deletion and pagination (Phase 6)."""
from __future__ import annotations


def _channel(make_session):
    c = make_session()
    c.register("alice", "alice@example.com", "password123")
    c.fetch_csrf()
    sid = c.post("/api/servers/", json_data={"name": "Guild"}).json()["server"]["id"]
    cid = c.post(f"/api/servers/{sid}/channels",
                 json_data={"name": "general"}).json()["channel"]["id"]
    return c, cid


def test_send_and_history(make_session):
    c, cid = _channel(make_session)
    r = c.post(f"/api/channels/{cid}/messages", json_data={"content": "hello"})
    assert r.status_code == 200
    mid = r.json()["message"]["id"]

    r = c.get(f"/api/channels/{cid}/messages")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == mid
    assert items[0]["content"] == "hello"


def test_empty_message_rejected(make_session):
    c, cid = _channel(make_session)
    assert c.post(f"/api/channels/{cid}/messages", json_data={"content": "   "}).status_code == 400


def test_message_too_long_rejected(make_session):
    c, cid = _channel(make_session)
    long = "x" * 5000
    assert c.post(f"/api/channels/{cid}/messages", json_data={"content": long}).status_code == 400


def test_delete_own_message(make_session):
    c, cid = _channel(make_session)
    mid = c.post(f"/api/channels/{cid}/messages", json_data={"content": "bye"}).json()["message"]["id"]
    assert c.delete(f"/api/channels/{cid}/messages/{mid}").status_code == 200
    items = c.get(f"/api/channels/{cid}/messages").json()["items"]
    assert all(m["id"] != mid for m in items)


def test_pagination_uses_cursor(make_session):
    c, cid = _channel(make_session)
    for i in range(5):
        c.post(f"/api/channels/{cid}/messages", json_data={"content": f"m{i}"})
    # First page of 2, then page back using the oldest id as cursor.
    page = c.get(f"/api/channels/{cid}/messages", query={"limit": "2"}).json()["items"]
    assert len(page) == 2
    oldest = page[0]["id"]
    older = c.get(f"/api/channels/{cid}/messages", query={"limit": "2", "before": str(oldest)}).json()["items"]
    assert len(older) == 2
    assert all(m["id"] < oldest for m in older)


def test_non_member_cannot_read_channel(make_session):
    owner, cid = _channel(make_session)  # cid belongs to alice's server
    sid = owner.get("/api/servers/").json()["items"][0]["id"]
    invite = owner.get(f"/api/servers/{sid}").json()["server"]["invite_code"]

    bob = make_session()
    bob.register("bob", "bob@example.com", "password123")
    bob.fetch_csrf()
    bob.post("/api/servers/join", json_data={"invite_code": invite})
    # bob is a member, so he CAN read — now prove a stranger cannot.
    stranger = make_session()
    stranger.register("eve", "eve@example.com", "password123")
    stranger.fetch_csrf()
    assert stranger.get(f"/api/channels/{cid}/messages").status_code == 403
