"""News and community module backed by the Flaxon CMS."""

from __future__ import annotations

from datetime import datetime

from flaxon.modules import FlaxonModule

community = FlaxonModule("community")
community.requires("cms")


def published_items(cms):
    content_type = cms.content_types["news"]
    return [item for item in content_type.items.values() if item.get("status") == "published"]


def display_items(cms):
    items = []
    for item in published_items(cms):
        record = dict(item)
        value = str(record.get("updated_at") or "")
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
            record["published_date"] = date.strftime("%b %d, %Y").replace(" 0", " ")
        except ValueError:
            record["published_date"] = "Recently"
        items.append(record)
    return items


@community.get("/news")
async def news_page(request, cms):
    items = display_items(cms)
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return await request.render("news.html", {"title": "Northstar news", "items": items})


@community.get("/api/news")
async def news_api(cms):
    return {"items": published_items(cms)}
