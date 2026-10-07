"""Body size accounting behavior and boundary cases."""

import pytest

from flaxon.exceptions import PayloadTooLarge
from flaxon.middleware.body_limit import BodyLimitMiddleware


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [None, b"1", b"invalid"])
async def test_chunked_body_is_counted_even_when_length_is_unreliable(length):
    chunks = iter([
        {"type": "http.request", "body": b"abc", "more_body": True},
        {"type": "http.request", "body": b"def", "more_body": False},
    ])

    async def receive():
        return next(chunks)

    async def downstream(scope, receive, send):
        await receive()
        await receive()

    headers = [] if length is None else [(b"content-length", length)]
    with pytest.raises(PayloadTooLarge):
        await BodyLimitMiddleware(downstream, max_size=5)({"type": "http", "headers": headers}, receive, None)


@pytest.mark.asyncio
async def test_exact_limit_is_accepted():
    bodies = []

    async def receive():
        return {"type": "http.request", "body": b"12345"}

    async def downstream(scope, receive, send):
        bodies.append((await receive())["body"])

    await BodyLimitMiddleware(downstream, max_size=5)({"type": "http", "headers": []}, receive, None)
    assert bodies == [b"12345"]
