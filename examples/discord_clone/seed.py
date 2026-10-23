"""Load demo data for the Discord-clone course project, after `management.py migrate`.

Run with:

    python management.py migrate
    python seed.py

Safe to re-run: rows that already exist are left alone. This seeds a demo owner,
a second member, a server with public/private channels and a role, and an example
bot that is already in the server, subscribed to message events, and carrying a
/ping command — so the tutorial's bot lessons have something to poke at.
"""
from __future__ import annotations

import asyncio

from app import create_app
from models import (
    Bot,
    BotMembership,
    Channel,
    EventSubscription,
    Membership,
    Role,
    Server,
    SlashCommand,
    User,
)
from services.auth import register_user
from services.tokens import issue_token


DEMO_USERNAME = "demo"
DEMO_PASSWORD = "password123"
DEMO_EMAIL = "demo@example.test"

SECOND_USERNAME = "alice"
SECOND_EMAIL = "alice@example.test"

SERVER_NAME = "Flaxon HQ"
BOT_NAME = "Greeter"
CHANNELS = ["general", "random", ("staff", True)]  # (name, is_private)
ROLE_NAME = "Moderator"
ROLE_PERMISSIONS = 8  # MANAGE_CHANNELS — enough to show role-based gating


async def seed_orm() -> int:
    created = 0

    owner = await User.get_or_none(username=DEMO_USERNAME)
    if owner is None:
        owner = await register_user(DEMO_USERNAME, DEMO_EMAIL, DEMO_PASSWORD)
        created += 1

    alice = await User.get_or_none(username=SECOND_USERNAME)
    if alice is None:
        alice = await register_user(SECOND_USERNAME, SECOND_EMAIL, DEMO_PASSWORD)
        created += 1

    server = await Server.get_or_none(name=SERVER_NAME, owner_id=owner.id)
    if server is None:
        server = await Server.create(name=SERVER_NAME, owner=owner, invite_code="flaxonhq")
        await Membership.create(server=server, user=owner)
        await Membership.create(server=server, user=alice)
        for index, spec in enumerate(CHANNELS):
            name, is_private = spec if isinstance(spec, tuple) else (spec, False)
            channel = await Channel.create(
                server=server, name=name, is_private=is_private, position=index
            )
            if is_private:
                # The owner can always see the private channel they seeded.
                from models import ChannelAccess

                await ChannelAccess.create(channel=channel, user=owner, granted_by=owner)
        role = await Role.create(
            server=server, name=ROLE_NAME, permissions=ROLE_PERMISSIONS, color="#5865f2"
        )
        # Promote alice to Moderator to demonstrate role assignment.
        await Membership.filter(server_id=server.id, user_id=alice.id).update(role_id=role.id)
        created += 1

    bot = await Bot.get_or_none(name=BOT_NAME, owner_id=owner.id)
    if bot is None:
        bot = await Bot.create(owner=owner, name=BOT_NAME, description="Example course bot")
        await BotMembership.create(server=server, bot=bot)
        await EventSubscription.create(bot=bot, event_type="message.create")
        await SlashCommand.create(bot=bot, name="ping", description="Reply with pong!")
        raw, _ = await issue_token(bot, label="seed")
        print(f"Bot '{BOT_NAME}' one-time token: {raw}")
        created += 1

    return created


def seed_cms(app) -> int:
    cms = getattr(app, "cms", None)
    if cms is None:
        return 0
    content_type = cms.content_types.get("announcement")
    if content_type is None:
        return 0
    existing = {item.get("title") for item in content_type.items.values()}
    if "Welcome to Flaxon HQ" in existing:
        return 0
    content_type.create(
        {
            "title": "Welcome to Flaxon HQ",
            "body": "<p>This is a demo server seeded by <code>seed.py</code>. "
            "Try the Greeter bot with <code>/ping</code> or mention it by name.</p>",
            "pinned": True,
            "status": "published",
        }
    )
    cms._save(content_type)
    return 1


async def main() -> None:
    app = create_app()
    async with app.db:
        created = await seed_orm()
    written = seed_cms(app)
    print(f"ORM rows created: {created}")
    print(f"CMS items created: {written}")


if __name__ == "__main__":
    asyncio.run(main())
