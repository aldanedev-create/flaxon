"""Cms slug uniqueness behavior and boundary cases."""

from flaxon.admin.cms import CMSField, ContentType


def test_duplicate_titles_receive_unique_slugs():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    slugs = [content.create({"title": "Hello World"})["slug"] for _ in range(4)]
    assert slugs == ["hello-world", "hello-world-2", "hello-world-3", "hello-world-4"]


def test_explicit_slug_is_normalized():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    record = content.create({"title": "Post", "slug": "Hello World!"})
    assert record["slug"] == "hello-world"


def test_separate_content_types_do_not_share_slug_state():
    first = ContentType("article", fields=[CMSField("title", required=True)])
    second = ContentType("page", fields=[CMSField("title", required=True)])
    assert first.create({"title": "Home"})["slug"] == second.create({"title": "Home"})["slug"]
