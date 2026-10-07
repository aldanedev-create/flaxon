"""Streaming responses behavior and boundary cases."""

import asyncio

import pytest

from flaxon.http import StreamingResponse


@pytest.mark.parametrize("chunks", [[], [b"one"], [b"a", b"", b"b"]])
def test_sync_stream_chunk_order_and_termination(chunks):
    messages = []

    async def send(message):
        messages.append(message)

    asyncio.run(StreamingResponse(chunks)({"type": "http"}, None, send))
    assert messages[0]["type"] == "http.response.start"
    assert b"".join(m.get("body", b"") for m in messages) == b"".join(chunks)
    assert messages[-1]["more_body"] is False
    assert b"content-length" not in dict(messages[0]["headers"])


def test_async_stream_keeps_binary_content(app, client):
    @app.get("/stream")
    async def stream():
        async def chunks():
            yield b"first"
            yield b"second"

        return StreamingResponse(chunks())

    assert client.get("/stream").text == "firstsecond"
