"""Editable flower-shop application using Flaxon Admin, CMS, and WebSockets.

Run from the repository root with::

    python -m flaxon run examples.flower_shop_admin.app:app --reload --port 8000

The example uses the AdminStore for persistent Admin/CMS data. The catalog
model is intentionally small and in-memory so developers can replace it with
their own database model without learning extra framework machinery.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard, admin_model
from flaxon.admin.cms import CMS, CMSField, ContentType
from flaxon.jinax import Jinax
from flaxon.websocket import WebSocket, WebSocketDisconnect


ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
dev_mailbox: list[dict[str, str]] = []
orders: list[dict[str, Any]] = []


async def capture_password_reset(identifier: str, token: str) -> None:
    dev_mailbox.append({"to": identifier, "subject": "Petal & Stem password reset", "url": f"/admin/password-reset?token={token}"})


async def capture_email_verification(email: str, token: str) -> None:
    dev_mailbox.append({"to": email, "subject": "Petal & Stem email verification", "url": f"/admin/verify-email?token={token}"})

app = Flaxon("petal-and-stem", debug=True)
app.use_templates(Jinax(ROOT / "templates", auto_reload=True, strict_undefined=True))
app.mount_static("/shop-static", str(ROOT / "static"))

admin = AdminDashboard(
    app,
    config=AdminConfig(
        site_title="Petal & Stem",
        site_header="Petal & Stem Operations",
        index_title="Flower shop operations",
        timezone="UTC",
        settings={"environment": "development", "public_site": "http://127.0.0.1:8000"},
    ),
    storage_path=str(DATA / "admin.sqlite3"),
    upload_dir=str(DATA / "uploads"),
    url_prefix="/admin",
    password_reset_sender=capture_password_reset,
    email_verification_sender=capture_email_verification,
    # Keep enforcement off in the demo so an unverified user can log in and
    # request a verification message from Admin Profile. Enable this in prod.
    require_email_verification=False,
    users=[
        {
            "username": "owner",
            "password": os.getenv("FLORAL_ADMIN_PASSWORD", "Owner123!"),
            "email": "owner@petal-stem.test",
            "roles": ["administrator"],
            # Set FLORAL_MFA_SECRET to a base32 TOTP secret to require MFA
            # immediately. Otherwise enroll it at /admin/profile after login.
            **({"mfa_secret": os.environ["FLORAL_MFA_SECRET"]} if os.getenv("FLORAL_MFA_SECRET") else {}),
        },
        {
            "username": "florist",
            "password": os.getenv("FLORAL_EDITOR_PASSWORD", "Florist123!"),
            "email": "florist@petal-stem.test",
            "roles": ["editor"],
        },
    ],
)


@admin_model(
    list_display=["id", "name", "category", "price", "stock", "active"],
    search_fields=["name", "sku", "category"],
    list_filter=["category", "active"],
    fields=["name", "sku", "category", "price", "stock", "active", "image"],
)
class Flower:
    """Editable catalog model exposed at ``/admin/flower``."""

    _data: dict[str, dict[str, Any]] = {}
    _id_counter = 1

    @classmethod
    async def get_instances(cls) -> list[dict[str, Any]]:
        return list(cls._data.values())

    @classmethod
    async def get_instance(cls, id: str) -> dict[str, Any] | None:
        return cls._data.get(id)

    @classmethod
    async def create_instance(cls, data: dict[str, Any]) -> dict[str, Any]:
        flower_id = str(cls._id_counter)
        cls._id_counter += 1
        record = {"id": flower_id, "active": True, "stock": 0, **data}
        cls._data[flower_id] = record
        return record

    @classmethod
    async def update_instance(cls, id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if id not in cls._data:
            return None
        cls._data[id].update(data)
        return cls._data[id]

    @classmethod
    async def delete_instance(cls, id: str) -> bool:
        return cls._data.pop(id, None) is not None


async def restock(flowers: list[str]) -> None:
    """Bulk action used to exercise Admin action permissions and workflows."""
    for flower_id in flowers:
        record = await Flower.get_instance(flower_id)
        if record:
            await Flower.update_instance(flower_id, {"stock": int(record.get("stock", 0)) + 10})


admin.registry.get("flower").add_action("restock", restock)
admin.register_widget(lambda **_: {"title": "Today", "value": "Fresh flowers, fast delivery"})


cms = CMS(app, url_prefix="/admin/cms", title="Petal & Stem Content", auth=admin.auth)
cms.register(
    ContentType(
        name="story",
        label="Story",
        label_plural="Stories",
        fields=[
            CMSField("title", "Title", required=True),
            CMSField("body", "Body", type="richtext"),
            CMSField("hero_image", "Hero image", type="image"),
            CMSField("published_on", "Published on", type="datetime"),
            CMSField("status", "Status", type="select", choices=["draft", "review", "approved", "scheduled", "published", "archived"]),
        ],
        list_display=["title", "status", "updated_at"],
        list_filter=["status"],
        search_fields=["title", "body"],
    )
)


async def shop_overview(request):
    """Protected custom Admin page for exercising the complete example."""

    media = await admin._media_files()
    stories = cms.content_types["story"]
    published = sum(1 for item in stories.items.values() if item.get("status") == "published")
    return await request.render(
        "admin_shop_overview.html",
        {
            "title": "Shop overview",
            "flower_count": len(Flower._data),
            "story_count": len(stories.items),
            "published_count": published,
            "media_count": len(media),
            "order_count": len(orders),
            "admin_url": "/admin/",
            "cms_url": "/admin/cms/",
        },
    )


admin.add_view(
    shop_overview,
    "Shop overview",
    url="shop-overview",
    category="Commerce",
    icon="fa-store",
    permission="admin.view_dashboard",
)


def seed() -> None:
    if not Flower._data:
        for item in (
            {"name": "Spring Peony", "sku": "PEO-001", "category": "Bouquets", "price": 48, "stock": 12, "active": True},
            {"name": "Sunlit Tulips", "sku": "TUL-002", "category": "Seasonal", "price": 32, "stock": 24, "active": True},
            {"name": "Garden Rose Box", "sku": "ROS-003", "category": "Gifts", "price": 72, "stock": 8, "active": True},
        ):
            # The example's seed data is synchronous at import time; the Admin
            # model remains async for normal request handling.
            flower_id = str(Flower._id_counter)
            Flower._id_counter += 1
            Flower._data[flower_id] = {"id": flower_id, **item}
    stories = cms.content_types["story"]
    if not stories.items:
        stories.create({
            "title": "How to keep cut flowers fresh",
            "body": "<p>Trim stems, refresh the water, and keep the arrangement cool.</p>",
            "status": "published",
        })
        cms._save(stories)


seed()

MAX_HISTORY = 100
room_messages: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
room_members: dict[str, set[WebSocket]] = defaultdict(set)
room_lock = asyncio.Lock()


def load_room(room_id: str) -> deque[dict[str, Any]]:
    if room_id not in room_messages:
        saved = admin.store.get("chat", room_id, []) if admin.store else []
        room_messages[room_id].extend(saved[-MAX_HISTORY:])
    return room_messages[room_id]


def create_message(room_id: str, user: str, text: str) -> dict[str, Any]:
    message = {"id": uuid.uuid4().hex, "room": room_id, "user": user, "text": text, "created_at": int(time.time())}
    history = load_room(room_id)
    history.append(message)
    if admin.store:
        admin.store.set("chat", room_id, list(history))
    return message


@app.get("/")
async def home(request):
    return await request.render("index.html", {"title": "Petal & Stem", "admin_url": "/admin/login", "cms_url": "/admin/cms/", "chat_url": "/chat", "catalog_url": "/catalog"})


@app.get("/catalog")
async def catalog(request):
    """Custom public page showing Admin-managed flowers and media URLs."""
    media = await admin._media_files()
    flowers = list(Flower._data.values())
    return await request.render("catalog.html", {"title": "Petal & Stem catalog", "flowers": flowers, "media": media})


@app.post("/api/orders")
async def create_order(request):
    body = await request.json() or {}
    items = body.get("items", [])
    if not isinstance(items, list) or not items:
        return {"error": "Your cart is empty."}
    line_items = []
    total = 0.0
    for item in items:
        flower = Flower._data.get(str(item.get("id", ""))) if isinstance(item, dict) else None
        quantity = int(item.get("quantity", 0)) if isinstance(item, dict) else 0
        if flower is None or quantity < 1 or quantity > 99:
            return {"error": "One or more cart items are invalid."}
        price = float(flower.get("price", 0))
        line_items.append({"id": flower["id"], "name": flower["name"], "quantity": quantity, "price": price})
        total += price * quantity
    order = {"id": uuid.uuid4().hex[:10].upper(), "items": line_items, "total": round(total, 2), "created_at": int(time.time())}
    orders.append(order)
    return {"order": order}


@app.get("/stories")
async def stories_page(request):
    """Public CMS page for published stories, similar to a small blog front page."""
    stories = [
        story for story in cms.content_types["story"].items.values()
        if story.get("status", "draft") == "published"
    ]
    stories.sort(key=lambda story: story.get("updated_at", ""), reverse=True)
    return await request.render("stories.html", {"title": "Petal & Stem journal", "stories": stories, "admin_url": "/admin/login", "cms_url": "/admin/cms/"})


@app.get("/cms-lab")
async def cms_lab(request):
    """Developer-facing public page for checking CMS output and workflows."""
    story_type = cms.content_types["story"]
    return await request.render(
        "cms_lab.html",
        {
            "title": "CMS feature lab",
            "stories": list(story_type.items.values()),
            "taxonomy_count": len(cms.taxonomies),
            "comment_count": len(cms.comments),
            "menu_count": len(cms.menus),
            "admin_url": "/admin/login",
            "cms_url": "/admin/cms/",
        },
    )


@app.get("/dev/mail")
async def dev_mail(request):
    """Development-only inbox for exercising reset and verification links."""
    return await request.render("mail.html", {"title": "Development mail inbox", "messages": list(reversed(dev_mailbox))})


@app.get("/chat")
async def chat_page(request):
    return await request.render("chat.html", {"title": "Petal & Stem team chat", "room": "shop-floor"})


@app.get("/api/chat/<room_id>/messages")
async def chat_history(room_id: str):
    return {"room": room_id, "messages": list(load_room(room_id))}


@app.websocket("/ws/chat/<room_id>")
async def chat(socket: WebSocket, room_id: str):
    query = socket.scope.get("query_string", b"").decode()
    user = next((part.split("=", 1)[1] for part in query.split("&") if part.startswith("user=")), "guest")[:40] or "guest"
    await socket.accept()
    await socket.join(room_id)
    async with room_lock:
        room_members[room_id].add(socket)
    await socket.send_json({"type": "ready", "room": room_id, "user": user, "messages": list(load_room(room_id))})
    await app.websocket_manager.broadcast_json(room_id, {"type": "presence.joined", "user": user})
    try:
        async for payload in socket.iter_json():
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "message.send":
                text = str(payload.get("text", "")).strip()
                if text and len(text) <= 4000:
                    await app.websocket_manager.broadcast_json(room_id, {"type": "message", "message": create_message(room_id, user, text)})
            elif payload.get("type") in {"typing", "ping"}:
                await app.websocket_manager.broadcast_json(room_id, {"type": payload["type"], "user": user})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        async with room_lock:
            room_members[room_id].discard(socket)
        await socket.leave(room_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.flower_shop_admin.app:app", host="127.0.0.1", port=8000, reload=True)
