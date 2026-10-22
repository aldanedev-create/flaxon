"""Bot token issuance and verification.

The plaintext token is shown to the owner exactly once. We store only the
SHA-256 hash plus a short prefix for display. This is the same one-way
storage pattern you would use for any credential — never persist the secret.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from models import Bot, BotToken


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def issue_token(bot: Bot, label: str = "default") -> tuple[str, BotToken]:
    """Create a token; returns (plaintext, record). The plaintext is one-time."""
    raw = "dc." + secrets.token_urlsafe(32)
    record = await BotToken.create(
        bot=bot,
        token_hash=_hash_token(raw),
        token_prefix=raw[:12],
        label=label,
    )
    return raw, record


async def verify_token(raw: str) -> BotToken | None:
    if not raw or not raw.startswith("dc."):
        return None
    record = await BotToken.get_or_none(token_hash=_hash_token(raw), revoked_at=None)
    if record is None:
        return None
    record.last_used_at = datetime.now(timezone.utc)
    await record.save(update_fields=["last_used_at"])
    return record


async def revoke_token(token_id: int) -> None:
    from datetime import datetime as _dt

    record = await BotToken.get_or_none(id=token_id)
    if record is None or record.revoked_at is not None:
        return
    record.revoked_at = _dt.now(timezone.utc)
    await record.save(update_fields=["revoked_at"])
