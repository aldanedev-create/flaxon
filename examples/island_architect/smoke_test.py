"""End-to-end smoke test for Island Architect.

Starts its own server on a throwaway database, then checks:

  * the Teloce shell compiles and every authored module is served
  * the JSON API round-trips a design through the ORM (create, list, update, delete)
  * server-side validation rejects a design the simulator could not run (422)
  * unknown ids return 404 instead of leaking a stack trace

Run:

    python smoke_test.py
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))

GRAPH = {
    "nodes": [
        {"id": "guest-app", "name": "Guest app", "kind": "client", "region": "montego-bay", "replicas": 1},
        {"id": "gateway", "name": "Island gateway", "kind": "edge", "region": "kingston", "replicas": 2},
        {"id": "ledger", "name": "Booking ledger", "kind": "db", "region": "kingston", "replicas": 1},
    ],
    "edges": [{"from": "guest-app", "to": "gateway"}, {"from": "gateway", "to": "ledger"}],
}

BROKEN_GRAPH = {
    "nodes": [{"id": "a", "name": "A", "kind": "spaceship", "region": "kingston", "replicas": 1}],
    "edges": [{"from": "a", "to": "ghost"}],
}

failures: list[str] = []


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(command, env, **kwargs):
    return subprocess.run(
        [sys.executable, *command], cwd=HERE, env=env, capture_output=True, text=True, **kwargs
    )


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="island_architect_")
    env = dict(os.environ, FLAXON_DEBUG="true", DATABASE_URL=f"sqlite://{os.path.join(tmp, 'island.sqlite3')}")

    for step in ("makemigrations", "migrate"):
        result = run(["management.py", step], env)
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

        # ---------------------------------------------------------- shell
        shell = session.get(url + "/").text
        check("SPA shell renders", "Island Architect" in shell)
        check("compiled entry is a module", "/_flaxon/ui/app.js" in shell)

        for asset in (
            "/_flaxon/ui/app.js",
            "/_flaxon/ui/components/NodeEditor.js",
            "/_flaxon/ui/components/TopoMap.js",
            "/_flaxon/ui/components/SimPanel.js",
            "/_flaxon/ui/components/LessonPane.js",
            "/_flaxon/static/js/island.js",
            "/_flaxon/static/js/sim.js",
            "/_flaxon/static/js/api.js",
            "/_flaxon/static/js/lessons.js",
        ):
            check(f"served {asset}", session.get(url + asset).status_code == 200)

        # ------------------------------------------------------------ API
        created = session.post(
            url + "/api/designs",
            json={"name": "Smoke design", "scenario": "storm", "seed": 99, "graph": GRAPH},
        )
        check("POST /api/designs creates (201)", created.status_code == 201, str(created.status_code))
        design_id = created.json().get("id")
        check("created design has an id", design_id is not None)

        items = session.get(url + "/api/designs").json()["items"]
        check("GET /api/designs lists it", any(item["id"] == design_id for item in items))
        check("list view counts nodes", items[0]["node_count"] == 3, str(items[0]))

        fetched = session.get(url + f"/api/designs/{design_id}").json()
        check("GET one returns the graph", fetched["graph"]["nodes"][0]["id"] == "guest-app")

        updated = session.put(url + f"/api/designs/{design_id}", json={"name": "Smoke v2", "seed": 5})
        check("PUT updates name and seed", updated.status_code == 200 and updated.json()["seed"] == 5)
        check(
            "update persisted",
            session.get(url + f"/api/designs/{design_id}").json()["name"] == "Smoke v2",
        )

        bad = session.post(url + "/api/designs", json={"name": "Broken", "graph": BROKEN_GRAPH})
        check("POST rejects an unknown kind (422)", bad.status_code == 422, str(bad.status_code))
        check("422 explains the problem", "spaceship" in bad.text)

        check("POST without a name is rejected", session.post(url + "/api/designs", json={}).status_code == 422)
        check("GET unknown id is 404", session.get(url + "/api/designs/99999").status_code == 404)
        check("scenarios are listed", "peak-season" in session.get(url + "/api/scenarios").text)

        deleted = session.delete(url + f"/api/designs/{design_id}")
        check("DELETE removes it", deleted.status_code == 200)
        check("GET after delete is 404", session.get(url + f"/api/designs/{design_id}").status_code == 404)
    finally:
        proc.kill()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
