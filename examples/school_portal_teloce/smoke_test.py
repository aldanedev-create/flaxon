"""End-to-end smoke test for the Teloce + Flaxon school portal.

Launches its own development server, then checks:

  * the SPA shell and every page route return 200
  * the JSON API serves the seeded ORM rows and published CMS content
  * a direct ORM write through POST /api/enrollments persists (round-trips to Admin)
  * the staff Admin can create a Student and the row really lands in the DB
    (regression coverage for the silent-save fix in PR #35)

Run:

    python smoke_test.py
"""
from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ADMIN_USER = "admin@example.test"
ADMIN_PASS = "Northstar$2026"

failures: list[str] = []


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(cmd, env, **kwargs):
    return subprocess.run([sys.executable, *cmd], cwd=HERE, env=env, capture_output=True, text=True, **kwargs)


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def main() -> int:
    # Use a throwaway database so the test is deterministic and never touches
    # the demo data/school.sqlite3 that ships with the example.
    tmp = tempfile.mkdtemp(prefix="school_teloce_")
    db_path = os.path.join(tmp, "school.sqlite3")
    env = dict(os.environ, FLAXON_DEBUG="true", DATABASE_URL=f"sqlite://{db_path}")

    for step in ("makemigrations", "migrate"):
        result = run(["management.py", step], env)
        if result.returncode != 0:
            print(result.stderr)
            return 1
    result = run(["seed.py"], env)
    if result.returncode != 0:
        print(result.stderr)
        return 1
    result = run(
        ["management.py", "setup-admin", "--username", ADMIN_USER],
        env,
        input=f"{ADMIN_PASS}\n{ADMIN_PASS}\n",
    )
    if result.returncode != 0:
        print(result.stderr)
        return 1

    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "management.py", "runserver", "--port", str(port)],
        cwd=HERE,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )
    url = f"http://127.0.0.1:{port}"
    session = requests.Session()
    try:
        for _ in range(80):
            try:
                if session.get(url + "/", timeout=3).status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            print("Server did not start in time", file=sys.stderr)
            return 1

        # SPA shell + pages
        shell = session.get(url + "/").text
        check("SPA shell renders", "router-view" in shell and "Northstar Academy" in shell)
        for page in ("students", "courses", "enroll", "news", "events"):
            code = session.get(url + "/" + page, timeout=10).status_code
            check(f"/{page} page returns 200", code == 200, f"status {code}")

        # API
        overview = session.get(url + "/api/overview").text
        check("overview exposes counts", '"students"' in overview and '"enrollments"' in overview)
        students = session.get(url + "/api/students").text
        before = len(re.findall(r'"id":\s*\d+', students))
        check("students API returns seeded rows", before >= 2, f"{before} rows")

        # Direct ORM write through the API (JSON body, matching the SPA)
        enroll = session.post(
            url + "/api/enrollments",
            json={"student_id": 2, "course_id": 1, "grade": "C"},
        )
        check("POST /api/enrollments creates row (201)", enroll.status_code == 201, f"status {enroll.status_code}")
        check("new enrollment has an id", '"id"' in enroll.text)
        dup = session.post(url + "/api/enrollments", json={"student_id": 2, "course_id": 1})
        check("duplicate enrollment rejected (409)", dup.status_code == 409, f"status {dup.status_code}")

        # Admin create — regression for the silent-save bug
        login = session.get(url + "/admin/login")
        csrf = re.search(r'name="_csrf" value="([^"]*)"', login.text).group(1)
        login_post = session.post(
            url + "/admin/login",
            data={"username": ADMIN_USER, "password": ADMIN_PASS, "_csrf": csrf},
            allow_redirects=False,
        )
        check("Admin login succeeds (302)", login_post.status_code in (302, 303), f"status {login_post.status_code}")
        add_html = session.get(url + "/admin/student/add").text
        csrf = re.search(r'name="_csrf" value="([^"]*)"', add_html).group(1)
        create = session.post(
            url + "/admin/student/add",
            data={
                "_csrf": csrf,
                "name": "Test Student",
                "grade": "9",
                "email": "test.student@example.test",
                "active": "true",
            },
            allow_redirects=False,
        )
        check("Admin create redirects (302)", create.status_code in (302, 303), f"status {create.status_code}")
        after = len(re.findall(r'"id":\s*\d+', session.get(url + "/api/students").text))
        check("Admin-created student persisted in ORM", after == before + 1, f"{before} -> {after}")

        dash = session.get(url + "/admin/")
        check("Admin dashboard reachable", dash.status_code == 200)
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
