"""Measure how well a fresh agent can answer Flaxon tasks using only AI docs.

The acceptance criterion for Phase 6 is an automated check that asks a fresh
agent session 10 Flaxon tasks using only ``llms.txt`` (and its full bundle),
then reports the real pass rate — even if low.

This script is the harness: it holds the 10 tasks and an answer key, and scores
a JSON mapping of ``task_id -> answer text``. To run a fresh session:

1. Start a new agent with no repo context.
2. Give it only ``llms.txt`` and ``llms-full.txt`` as reading material.
3. Ask each question in ``TASKS`` and collect its answer.
4. Save ``{"task_id": "answer"}`` to a file and run ``--answers FILE``.

``--self-test`` runs the key against itself (expected 10/10) to prove the
scorer works; it is not a substitute for the fresh-agent run.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TASKS: list[dict[str, object]] = [
    {
        "id": "route_syntax",
        "question": "What is the correct route syntax for a typed integer path parameter in Flaxon?",
        "patterns": [r"<int:id>"],
    },
    {
        "id": "openapi",
        "question": "How do you enable the /docs page in Flaxon?",
        "patterns": [r"openapi\s*=\s*True"],
    },
    {
        "id": "websockets_extra",
        "question": "Which install extra do you need so WebSockets work (not return 404)?",
        "patterns": [r"flaxon\[standard\]"],
    },
    {
        "id": "validation_code",
        "question": "What error code and HTTP status does a Flaxon validation error use?",
        "patterns": [r"FX-VAL-001", r"422"],
    },
    {
        "id": "post_json_kwarg",
        "question": "Which keyword does TestClient.post use to send a JSON body?",
        "patterns": [r"json_data"],
    },
    {
        "id": "templates",
        "question": "List the valid flaxon new --template names.",
        "patterns": [r"basic", r"api-db", r"fullstack"],
    },
    {
        "id": "min_deps",
        "question": "What are the three minimum runtime dependencies of Flaxon?",
        "patterns": [r"orjson", r"PyJWT", r"argon2"],
    },
    {
        "id": "ws_origin",
        "question": "What close code rejects a bad WebSocket Origin before handshake?",
        "patterns": [r"1008"],
    },
    {
        "id": "admin_registration",
        "question": "How do you turn a model into a full admin in Flaxon?",
        "patterns": [r"Resource", r"register"],
    },
    {
        "id": "teloce_field",
        "question": "What class do you use for a Teloce-backed admin field, and what does it require?",
        "patterns": [r"TeloceField", r"Component"],
    },
]


# Known-good answers used only by --self-test to prove the scorer works.
SELF_TEST_ANSWERS: dict[str, str] = {
    "route_syntax": "Use <int:id> converters, not {id}.",
    "openapi": "Flaxon('app', openapi=True) enables /docs.",
    "websockets_extra": "Install flaxon[standard].",
    "validation_code": "HTTP 422 with error.code FX-VAL-001 and error.fields.",
    "post_json_kwarg": "Use json_data= to send a JSON body.",
    "templates": "basic, api, api-db, web, fullstack",
    "min_deps": "orjson, PyJWT and argon2-cffi.",
    "ws_origin": "Close code 1008.",
    "admin_registration": "A Resource subclass then dashboard.register(...).",
    "teloce_field": "TeloceField with a Component and HTML fallback.",
}


def score(answers: dict[str, str]) -> tuple[int, list[str], list[str]]:
    """Return (passed, failed, missed tasks) for an answer mapping."""
    passed: list[str] = []
    failed: list[str] = []
    for task in TASKS:
        task_id = str(task["id"])
        answer = str(answers.get(task_id, ""))
        patterns = task["patterns"]
        assert isinstance(patterns, list)
        if all(re.search(pattern, answer, re.I) for pattern in patterns):
            passed.append(task_id)
        else:
            failed.append(task_id)
    return len(passed), failed, list(failed)


def main() -> int:
    """Score an answer file or run the scorer self-test."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path, help="JSON file mapping task_id -> answer")
    parser.add_argument("--self-test", action="store_true", help="score the answer key against itself")
    args = parser.parse_args()

    if args.self_test:
        passed, failed, _ = score(SELF_TEST_ANSWERS)
        print(f"self-test: {passed}/{len(TASKS)} passed")
        return 0 if passed == len(TASKS) else 1

    if not args.answers:
        print("Provide --answers FILE or --self-test")
        return 2
    answers = json.loads(args.answers.read_text(encoding="utf-8"))
    passed, failed, _ = score(answers)
    total = len(TASKS)
    print(f"llms.txt agent pass rate: {passed}/{total} ({passed / total:.0%})")
    if failed:
        print("Failed tasks:", ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
