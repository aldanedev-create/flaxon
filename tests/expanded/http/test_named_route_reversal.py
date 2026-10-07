"""Named route reversal behavior and boundary cases."""

import pytest

from flaxon.routing import Router


def test_reverse_typed_parameters():
    router = Router(prefix="/api")

    @router.get("/jobs/<int:job_id>", name="job-detail")
    async def endpoint(job_id):
        return job_id

    assert router.url_for("job-detail", job_id=42) == "/api/jobs/42"


def test_unknown_named_route_is_explicit_error():
    with pytest.raises(KeyError):
        Router().url_for("missing")


def test_missing_reverse_parameter_is_explicit_error():
    router = Router()

    @router.get("/<int:item_id>", name="item")
    async def endpoint(item_id):
        return item_id

    with pytest.raises(KeyError):
        router.url_for("item")
