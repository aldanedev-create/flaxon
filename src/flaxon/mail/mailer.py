from __future__ import annotations

from typing import Any

from flaxon._imports import import_attribute

from .message import Email


class Mailer:
    """Mailer implementation for the mail subsystem."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    async def send(self, email: Email | str) -> None:
        """Perform the send operation for mailer."""
        if isinstance(email, str):
            email = Email(to=[], from_address="", body=email)

        if hasattr(self.adapter, "send"):
            result = self.adapter.send(email)
            if hasattr(result, "__await__"):
                await result
            return

        raise NotImplementedError("Adapter does not support send")

    async def send_many(self, emails: list[Email]) -> None:
        """Send the many."""
        for email in emails:
            await self.send(email)

    async def send_template(self, template: Any, context: dict[str, Any], **kwargs: Any) -> None:
        """Send the template."""
        email = template.render(context, **kwargs)
        await self.send(email)

    def create_message(self) -> Any:
        """Create the message."""
        message_type = import_attribute("flaxon.mail.message", "Message")

        return message_type()
