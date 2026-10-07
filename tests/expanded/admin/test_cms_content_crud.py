"""Cms content crud behavior and boundary cases."""

import pytest

from flaxon.admin.cms import CMSField, ContentType
from flaxon.exceptions import BadRequest, NotFound


def test_create_update_delete_records():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    record = content.create({"title": "First post"})
    assert record["status"] == "draft"
    assert content.get(record["id"])["title"] == "First post"
    content.update(record["id"], {"title": "Edited post"})
    assert content.get(record["id"])["title"] == "Edited post"
    content.delete(record["id"])
    with pytest.raises(NotFound):
        content.get(record["id"])


def test_required_fields_block_creation():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    with pytest.raises(BadRequest):
        content.create({})
    assert content.items == {}


def test_unknown_fields_cannot_set_internal_id():
    content = ContentType("article", fields=[CMSField("title", required=True)])
    record = content.create({"title": "Post", "id": "forged", "owner": "attacker"})
    assert record["id"] != "forged"
    assert "owner" not in record
