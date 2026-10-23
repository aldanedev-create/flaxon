"""Message persistence and history pagination.

Messages are the single source of truth for chat history. The realtime hub
publishes them, but clients always recover from here after a reconnect, so a
missed WebSocket event can never lose durable data.
"""
from __future__ import annotations

from models import Message

MAX_MESSAGE_LENGTH = 4000
DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 200


async def create_message(
    channel_id: int,
    *,
    author_id: int | None = None,
    author_bot_id: int | None = None,
    content: str,
    message_type: int = Message.TYPE_USER,
) -> Message:
    content = (content or "").strip()
    if not content:
        raise ValueError("empty_message")
    if len(content) > MAX_MESSAGE_LENGTH:
        raise ValueError("message_too_long")
    if author_id is None and author_bot_id is None:
        raise ValueError("message_needs_author")
    return await Message.create(
        channel_id=channel_id,
        author_id=author_id,
        author_bot_id=author_bot_id,
        content=content,
        type=message_type,
    )


async def channel_history(
    channel_id: int,
    before_id: int | None = None,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[dict]:
    """Return up to `limit` messages older than `before_id`, oldest first.

    Cursor pagination by id (which is monotonic with created_at) keeps the
    query index-friendly and stable under concurrent inserts.
    """
    limit = max(1, min(limit, MAX_HISTORY_LIMIT))
    query = Message.filter(channel_id=channel_id)
    if before_id is not None:
        query = query.filter(id__lt=before_id)
    rows = await query.order_by("-id").limit(limit)
    rows.reverse()
    return [row.to_public() for row in rows]
