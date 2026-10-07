"""Cms revision history behavior and boundary cases."""

from flaxon.admin.cms import CMSField, ContentType


def test_revisions_preserve_prior_values():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    record = content.create({"title": "Original"})
    content.update(record["id"], {"title": "Edited"})
    assert content.revisions[0]["record"]["title"] == "Original"
    assert content.revisions[-1]["record"]["title"] == "Edited"


def test_multiple_updates_form_ordered_history():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    record = content.create({"title": "One"})
    content.update(record["id"], {"title": "Two"})
    content.update(record["id"], {"title": "Three"})
    assert [r["record"]["title"] for r in content.revisions] == ["One", "Two", "Three"]


def test_other_record_revision_is_not_changed():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    first = content.create({"title": "First"})
    second = content.create({"title": "Second"})
    content.update(second["id"], {"title": "Updated"})
    assert content.get(first["id"])["title"] == "First"
