import re
from urllib.parse import urlencode

import pytest

from examples.school_portal.app import app as school_app
from flaxon.testing import AsyncTestClient, TestClient


def test_school_portal_public_modules_and_cms() -> None:
    client = TestClient(school_app)

    home = client.get("/")
    assert home.status_code == 200
    assert "Northstar Academy" in home.text

    courses = client.get("/academics/courses")
    assert courses.status_code == 200
    assert "General Science" in courses.text

    academics = client.get("/academics")
    assert academics.status_code == 200
    assert "A curriculum with range" in academics.text

    for path, marker in (("/students", "Student life"), ("/admissions", "Admissions"), ("/contact", "Contact Northstar")):
        page = client.get(path)
        assert page.status_code == 200
        assert marker in page.text

    calendar = client.get("/calendar")
    assert calendar.status_code == 200
    assert "Family welcome evening" in calendar.text

    api = client.get("/api/courses")
    assert api.status_code == 200
    assert api.json()["courses"][0]["code"] == "SCI-101"

    news = client.get("/news")
    assert news.status_code == 200
    assert "Welcome to Northstar" in news.text
    assert "news-feature" in news.text
    assert "The Northstar bulletin" in news.text


def test_school_portal_admin_routes_and_custom_page() -> None:
    client = TestClient(school_app)

    assert client.get("/admin/login").status_code == 200
    assert client.get("/admin/student").status_code == 401
    assert client.get("/admin/school-overview").status_code == 401
    assert client.get("/admin/cms/").status_code == 401


@pytest.mark.asyncio
async def test_school_portal_admin_template_uses_admin_loader_fallback() -> None:
    dashboard = school_app._flaxon_admin_dashboard
    html = await dashboard.jinax.render(
        "admin_school_overview.html",
        {
            "student_count": 2,
            "course_count": 3,
            "staff_count": 2,
            "news_count": 1,
            "admin_url": "/admin/",
            "cms_url": "/admin/cms/",
        },
    )
    assert "Northstar school overview" in html


@pytest.mark.asyncio
async def test_school_portal_admin_cookie_survives_public_navigation() -> None:
    client = AsyncTestClient(school_app)
    login_page = await client.get("/admin/login")
    csrf = re.search(r'name="_csrf" value="([^"]+)"', login_page.text)
    assert csrf is not None

    login = await client.post(
        "/admin/login",
        content=urlencode(
            {"username": "admin", "password": "School123!", "_csrf": csrf.group(1)}
        ),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 302
    sessions = school_app._flaxon_admin_dashboard.store.list("sessions")
    session_id = max(
        sessions.items(), key=lambda item: item[1].get("created_at", 0)
    )[0]
    session_cookie = f"session_id={session_id}"

    assert (await client.get("/", headers={"cookie": session_cookie})).status_code == 200
    login_again = await client.get("/admin/login", headers={"cookie": session_cookie})
    assert login_again.status_code == 302
    assert login_again.headers["location"] == "/admin/"
    assert (await client.get("/admin/", headers={"cookie": session_cookie})).status_code == 200
