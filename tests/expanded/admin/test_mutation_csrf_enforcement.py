"""Mutation csrf enforcement behavior and boundary cases."""

import pytest


@pytest.mark.parametrize("token", [None, "invalid"])
def test_user_update_requires_valid_explicit_csrf(admin_headers, dashboard, client, token):
    headers = {"cookie": admin_headers["cookie"]}
    if token is not None:
        headers["x-csrf-token"] = token
    response = client.patch(
        "/admin/users/reader", json_data={"email": "changed@example.com"}, headers=headers
    )
    assert response.status_code == 403
    assert dashboard.auth.users["reader"].get("email") is None


def test_valid_csrf_allows_authorized_update(admin_headers, dashboard, client):
    response = client.patch(
        "/admin/users/reader", json_data={"email": "reader@example.com"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert dashboard.auth.users["reader"]["email"] == "reader@example.com"


def test_self_delete_is_rejected(admin_headers, dashboard, client):
    response = client.delete("/admin/users/admin", headers=admin_headers)
    assert response.status_code == 400
    assert "admin" in dashboard.auth.users
