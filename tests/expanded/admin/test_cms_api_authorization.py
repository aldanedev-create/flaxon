"""Cms api authorization behavior and boundary cases."""

import pytest

from flaxon.admin.cms import CMS, CMSField, ContentType


@pytest.mark.parametrize("action", ["POST", "DELETE"])
def test_reader_cannot_mutate_cms(dashboard, reader_headers, app, client, action):
    cms = CMS(app)
    content = cms.register(ContentType("article", fields=[CMSField("title", required=True)]))
    record = content.create({"title": "Protected"})
    path = (
        "/admin/cms/api/article/items" if action == "POST" else "/admin/cms/api/article/items/" + record["id"]
    )
    response = client.request(action, path, json_data={"title": "Attack"}, headers=reader_headers)
    assert response.status_code == 403
    assert len(content.items) == 1
    assert content.get(record["id"])["title"] == "Protected"


def test_admin_can_create_cms_content(dashboard, admin_headers, app, client):
    cms = CMS(app)
    cms.register(ContentType("article", fields=[CMSField("title", required=True)]))
    response = client.post(
        "/admin/cms/api/article/items", json_data={"title": "Approved"}, headers=admin_headers
    )
    assert response.status_code in {200, 201}
    assert len(cms.content_types["article"].items) == 1
