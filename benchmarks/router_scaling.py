"""Route lookup only: common-prefix static/dynamic hits, 404s, and 405s."""

import argparse
import json
import logging
import platform
import statistics
import time

from flaxon.exceptions import MethodNotAllowed, NotFound
from flaxon.routing.router import Router

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--iterations", type=int, default=3000)
args = parser.parse_args()
if args.iterations < 1:
    parser.error("--iterations must be positive")
logging.disable(logging.CRITICAL)


def endpoint():
    """Provide a minimal endpoint for registration."""
    return


def measure(function):
    """Return the median nanoseconds per verified lookup."""
    samples = []
    for _ in range(7):
        start = time.perf_counter_ns()
        for i in range(args.iterations):
            function(i)
        samples.append((time.perf_counter_ns() - start) / args.iterations)
    return round(statistics.median(samples), 1)


result = {"python": platform.python_version(), "unit": "ns/lookup", "cases": {}}
for count in (10, 100, 1000):
    router = Router()
    for i in range(count):
        router.get(f"/api/resource{i}/<int:object_id>")(endpoint)
        router.get(f"/api/resource{i}/summary")(endpoint)

    def dynamic(i, router=router, count=count):
        """Verify a typed dynamic route lookup."""
        match = router.match(f"/api/resource{i % count}/{i + 1}", "GET")
        assert match.params["object_id"] == i + 1

    def static(i, router=router, count=count):
        """Look up an exact literal route."""
        router.match(f"/api/resource{i % count}/summary", "GET")

    def missing(i, router=router, count=count):
        """Verify an unknown resource returns 404."""
        try:
            router.match("/api/missing/42", "GET")
        except NotFound:
            return
        raise AssertionError("expected 404")

    def wrong_method(i, router=router, count=count):
        """Verify a known resource rejects an unsupported method."""
        try:
            router.match(f"/api/resource{i % count}/{i + 1}", "POST")
        except MethodNotAllowed:
            return
        raise AssertionError("expected 405")

    result["cases"][str(count)] = {
        name: measure(fn)
        for name, fn in [
            ("dynamic", dynamic),
            ("static", static),
            ("missing", missing),
            ("wrong_method", wrong_method),
        ]
    }
print(json.dumps(result, indent=2))
