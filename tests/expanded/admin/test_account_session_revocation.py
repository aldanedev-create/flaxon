"""Account session revocation behavior and boundary cases."""


def test_deactivated_reader_session_stops_working(admin_headers, reader_headers, dashboard, client):
    assert client.get("/admin/profile", headers=reader_headers).status_code == 200
    result = client.patch("/admin/users/reader", json_data={"active": False}, headers=admin_headers)
    assert result.status_code == 200
    assert client.get("/admin/profile", headers=reader_headers).status_code == 401


def test_deleted_reader_session_stops_working(admin_headers, reader_headers, dashboard, client):
    result = client.delete("/admin/users/reader", headers=admin_headers)
    assert result.status_code == 200
    assert client.get("/admin/profile", headers=reader_headers).status_code == 401


def test_reduced_permissions_apply_to_existing_session(admin_headers, reader_headers, dashboard, client):
    result = client.patch(
        "/admin/users/reader", json_data={"permissions": [], "roles": []}, headers=admin_headers
    )
    assert result.status_code == 200
    assert client.get("/admin/profile", headers=reader_headers).status_code == 403
