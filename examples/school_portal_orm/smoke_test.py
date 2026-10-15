"""End-to-end smoke test for the ORM school portal.

Start the server first:

    python management.py runserver --port 8010 --no-reload

Then:

    python smoke_test.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE = "http://127.0.0.1:8010"
DB = Path(__file__).resolve().parent / "data" / "school.sqlite3"

PAGES = [
    "/",
    "/about",
    "/academics",
    "/academics/courses",
    "/students",
    "/admissions",
    "/calendar",
    "/news",
    "/contact",
    "/api/courses",
    "/api/news",
    "/admin/login",
]


def csrf_from(html: str) -> str | None:
    match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else None


def hidden_fields(html: str) -> dict[str, str]:
    """Every hidden input, including the `_version` record fingerprint."""
    return {
        name: value
        for name, value in re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
    }


def rows(table: str) -> int:
    con = sqlite3.connect(DB)
    try:
        return con.execute(f"select count(*) from {table}").fetchone()[0]
    finally:
        con.close()


def main() -> int:
    session = requests.Session()
    failures = []

    print("== public pages ==")
    for path in PAGES:
        response = session.get(BASE + path, timeout=20)
        ok = response.status_code == 200
        print(f"  {response.status_code}  {path}")
        if not ok:
            failures.append(path)

    courses = session.get(BASE + "/api/courses", timeout=20).json()["courses"]
    print(f"  /api/courses -> {len(courses)} rows: {[c['code'] for c in courses]}")
    if not courses:
        failures.append("api/courses empty")

    print("== admin sign-in ==")
    login_page = session.get(BASE + "/admin/login", timeout=20)
    token = csrf_from(login_page.text)
    response = session.post(
        BASE + "/admin/login",
        data={"username": "admin", "password": "School123!", "_csrf": token or ""},
        timeout=20,
        allow_redirects=False,
    )
    print(f"  login -> {response.status_code} {response.headers.get('location', '')}")
    if response.status_code not in (200, 302, 303):
        failures.append("login")

    print("== admin create (the path that used to silently fail) ==")
    before = rows("school_students")
    add_page = session.get(BASE + "/admin/student/add", timeout=20)
    token = csrf_from(add_page.text)
    payload = {
        "name": "Mia Okafor",
        "grade": "12",
        "email": "mia@example.test",
        "active": "on",
        "_csrf": token or "",
    }
    response = session.post(
        BASE + "/admin/student/add",
        data=payload,
        timeout=20,
        allow_redirects=False,
    )
    after = rows("school_students")
    print(f"  POST /admin/student/add -> {response.status_code} {response.headers.get('location', '')}")
    print(f"  rows in school_students: {before} -> {after}")
    if after != before + 1:
        failures.append("create did not persist")

    con = sqlite3.connect(DB)
    new_row = con.execute(
        "select id, name, grade, email, active from school_students where email = ?",
        ("mia@example.test",),
    ).fetchone()
    con.close()
    print(f"  stored row: {new_row}")
    if new_row is None:
        failures.append("row missing")

    print("== admin edit ==")
    student_id = new_row[0] if new_row else 1
    edit_page = session.get(f"{BASE}/admin/student/{student_id}/edit", timeout=20)
    # The ORM adapter writes conditionally, so the form's `_version` fingerprint
    # has to come back with the payload.
    payload = hidden_fields(edit_page.text)
    payload.update({"name": "Mia Okafor-Nwosu", "grade": "12", "email": "mia@example.test", "active": "on"})
    response = session.post(
        f"{BASE}/admin/student/{student_id}/edit",
        data=payload,
        timeout=20,
        allow_redirects=False,
    )
    con = sqlite3.connect(DB)
    updated = con.execute(
        "select name, active from school_students where id = ?", (student_id,)
    ).fetchone()
    con.close()
    print(f"  POST edit -> {response.status_code}; stored: {updated}")
    if not updated or updated[0] != "Mia Okafor-Nwosu":
        failures.append("edit did not persist")

    print("== admin delete ==")
    delete_page = session.get(f"{BASE}/admin/student/{student_id}/delete", timeout=20)
    token = csrf_from(delete_page.text)
    response = session.post(
        f"{BASE}/admin/student/{student_id}/delete",
        data={"_csrf": token or "", "confirm": "yes"},
        timeout=20,
        allow_redirects=False,
    )
    final = rows("school_students")
    print(f"  POST delete -> {response.status_code}; rows: {after} -> {final}")
    if final != after - 1:
        failures.append("delete did not persist")

    print("== admin dashboard + cms ==")
    for path in ("/admin/", "/admin/cms/", "/admin/school-overview", "/admin/student", "/admin/course", "/admin/staff"):
        response = session.get(BASE + path, timeout=20, allow_redirects=False)
        print(f"  {response.status_code}  {path}")
        if response.status_code >= 400:
            failures.append(path)

    print()
    if failures:
        print(f"FAILED ({len(failures)}): {failures}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
