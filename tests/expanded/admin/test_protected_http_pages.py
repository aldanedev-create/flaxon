"""Protected http pages behavior and boundary cases."""

import pytest


@pytest.mark.parametrize(
    "path", ["/admin", "/admin/users", "/admin/roles", "/admin/settings", "/admin/media", "/admin/operations"]
)
def test_anonymous_requests_cannot_open_protected_pages(dashboard, client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ["/admin/users", "/admin/roles", "/admin/settings", "/admin/media"])
def test_reader_cannot_open_privileged_pages(reader_headers, client, path):
    assert client.get(path, headers=reader_headers).status_code == 403


def test_login_page_is_public(dashboard, client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "password" in response.text.lower()
