"""Stream.json_lines / Stream.sse must build valid responses with correct media types."""

from __future__ import annotations

import asyncio

from flaxon.http.streaming import Stream


def _headers(response):
    messages = []

    async def send(message):
        messages.append(message)

    asyncio.run(response({"type": "http"}, None, send))
    return {
        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
        for k, v in messages[0]["headers"]
    }


def test_json_lines_streams_ndjson_with_correct_content_type():
    response = Stream.json_lines([{"a": 1}, {"a": 2}])
    headers = _headers(response)
    assert headers["content-type"] == "application/x-ndjson"


def test_sse_streams_with_correct_content_type():
    async def events():
        yield {"event": "update", "id": "1", "data": "hello"}

    response = Stream.sse(events())
    headers = _headers(response)
    assert headers["content-type"] == "text/event-stream"


def test_text_stream_default_remains_plain_text():
    response = Stream.text("hello", chunk_size=2)
    assert _headers(response)["content-type"].startswith("text/plain")
