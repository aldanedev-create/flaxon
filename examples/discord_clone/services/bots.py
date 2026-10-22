"""Bot platform: safe, in-process command and event execution.

Design constraints from the course spec:
- No arbitrary untrusted Python runs in the web process. Bot behaviour is a set
  of registered handler functions (see the example handlers below).
- Tokens are one-way hashed (services.tokens); this module never sees plaintext.
- Event delivery is idempotent per (bot, idempotency_key) and retried with
  exponential backoff, mirroring a real webhook dispatcher.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from models import (
    Bot,
    BotMembership,
    CommandInvocation,
    EventDelivery,
    EventSubscription,
    Message,
    SlashCommand,
)
from services.messages import create_message

MAX_DELIVERY_ATTEMPTS = 5

# Registries populated by the @command / @event_handler decorators.
COMMAND_HANDLERS: dict[str, callable] = {}
EVENT_HANDLERS: dict[str, list[callable]] = {}


def command(name: str):
    def decorator(fn):
        COMMAND_HANDLERS[name] = fn
        return fn
    return decorator


def event_handler(event_type: str):
    def decorator(fn):
        EVENT_HANDLERS.setdefault(event_type, []).append(fn)
        return fn
    return decorator


@dataclass
class BotContext:
    bot: Bot
    server_id: int | None = None
    channel_id: int | None = None
    user_id: int | None = None
    produced: list[Message] = field(default_factory=list)

    async def post_message(self, content: str) -> Message:
        message = await create_message(
            self.channel_id,
            author_bot_id=self.bot.id,
            content=content,
            message_type=Message.TYPE_BOT,
        )
        self.produced.append(message)
        return message


# --------------------------------------------------------------------------- #
# Example bot behaviour (registered automatically on import)
# --------------------------------------------------------------------------- #
@command("ping")
async def ping(ctx: BotContext, args) -> str:
    return "pong!"


@command("echo")
async def echo(ctx: BotContext, args) -> str:
    return " ".join(args) if args else "(nothing to echo)"


@command("help")
async def help_command(ctx: BotContext, args) -> str:
    names = ", ".join(sorted(COMMAND_HANDLERS)) or "none"
    return f"Available commands: {names}"


@event_handler("message.create")
async def on_message(ctx: BotContext, payload: dict) -> None:
    """Reply when a message mentions the bot by name or contains '!hello'."""
    content = (payload.get("content") or "").lower()
    if "!hello" in content or ctx.bot.name.lower() in content:
        author_id = payload.get("author_id")
        await ctx.post_message(f"Hello <@{author_id}>! I'm {ctx.bot.name}. Try /ping.")


# --------------------------------------------------------------------------- #
# Command execution
# --------------------------------------------------------------------------- #
async def execute_command(
    bot: Bot,
    command: SlashCommand,
    *,
    server_id: int,
    channel_id: int,
    user_id: int,
    args: list | None = None,
) -> tuple[CommandInvocation, list[Message]]:
    ctx = BotContext(bot=bot, server_id=server_id, channel_id=channel_id, user_id=user_id)
    status = CommandInvocation.STATUS_SUCCESS
    result, error = "", ""
    handler = COMMAND_HANDLERS.get(command.name)
    if command.is_enabled and handler is not None:
        try:
            output = await handler(ctx, args or [])
            result = "" if output is None else str(output)
        except Exception as exc:  # handler bugs must not crash the request
            status = CommandInvocation.STATUS_ERROR
            error = str(exc)[:500]
    else:
        status = CommandInvocation.STATUS_ERROR
        error = "command_disabled_or_unknown"
    invocation = await CommandInvocation.create(
        bot=bot,
        command=command,
        server_id=server_id,
        channel_id=channel_id,
        user_id=user_id,
        status=status,
        result=result,
        error=error,
    )
    return invocation, ctx.produced


# --------------------------------------------------------------------------- #
# Event delivery (idempotent + retry/backoff)
# --------------------------------------------------------------------------- #
async def attempt_delivery(bot: Bot, delivery: EventDelivery) -> tuple[EventDelivery, list[Message]]:
    handlers = EVENT_HANDLERS.get(delivery.event_type, [])
    ctx = BotContext(
        bot=bot,
        server_id=delivery.payload.get("server_id"),
        channel_id=delivery.payload.get("channel_id"),
        user_id=delivery.payload.get("author_id"),
    )
    delivery.attempt_count += 1
    try:
        for handler in handlers:
            await handler(ctx, delivery.payload)
        delivery.status = EventDelivery.STATUS_DELIVERED
        delivery.delivered_at = datetime.now(timezone.utc)
        delivery.last_error = None
    except Exception as exc:
        delivery.status = EventDelivery.STATUS_FAILED
        delivery.last_error = str(exc)[:500]
    await delivery.save()
    return delivery, ctx.produced


async def deliver_event(
    bot: Bot,
    event_type: str,
    payload: dict,
    idempotency_key: str,
) -> tuple[EventDelivery, list[Message]]:
    # Idempotency: a payload already delivered for this (bot, key) is a no-op.
    existing = await EventDelivery.get_or_none(
        bot_id=bot.id, idempotency_key=idempotency_key, status=EventDelivery.STATUS_DELIVERED
    )
    if existing is not None:
        return existing, []
    subscription = await EventSubscription.get_or_none(
        bot_id=bot.id, event_type=event_type, is_enabled=True
    )
    delivery = await EventDelivery.create(
        bot=bot,
        subscription=subscription,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload,
        status=EventDelivery.STATUS_PENDING,
    )
    return await attempt_delivery(bot, delivery)


async def retry_failed_deliveries() -> list[tuple[EventDelivery, list[Message]]]:
    """Retry deliveries that failed, honouring an exponential backoff window."""
    failed = await EventDelivery.filter(status=EventDelivery.STATUS_FAILED).all()
    results = []
    for delivery in failed:
        if delivery.attempt_count >= MAX_DELIVERY_ATTEMPTS:
            continue
        # Backoff proportional to prior attempts before retrying.
        await asyncio.sleep(min(2 ** delivery.attempt_count, 8))
        bot = await Bot.get(id=delivery.bot_id)
        results.append(await attempt_delivery(bot, delivery))
    return results


async def dispatch_message_event(message: Message, server_id: int, hub=None) -> list[Message]:
    """Fire message.create to every bot that is a member of the server and subscribed."""
    payload = {
        "server_id": server_id,
        "channel_id": message.channel_id,
        "author_id": message.author_id,
        "content": message.content,
        "message_id": message.id,
    }
    produced: list[Message] = []
    subscriptions = (
        await EventSubscription.filter(event_type="message.create", is_enabled=True)
        .prefetch_related("bot")
        .all()
    )
    for sub in subscriptions:
        bot = sub.bot
        membership = await BotMembership.get_or_none(server_id=server_id, bot_id=bot.id)
        if membership is None:
            continue
        # message.id makes the key unique, so retries never double-deliver.
        _delivery, messages = await deliver_event(
            bot, "message.create", payload, idempotency_key=f"msg:{message.id}"
        )
        produced.extend(messages)
    return produced
