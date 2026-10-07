"""Mail adapter dispatch behavior and boundary cases."""

import pytest

from flaxon.mail.mailer import Mailer
from flaxon.mail.message import Email


@pytest.mark.asyncio
async def test_sync_adapter_receives_each_message_in_order():
    sent = []

    class Adapter:
        def send(self, email):
            sent.append(email.subject)

    await Mailer(Adapter()).send_many([Email("from", subject="first"), Email("from", subject="second")])
    assert sent == ["first", "second"]


@pytest.mark.asyncio
async def test_async_adapter_is_awaited():
    sent = []

    class Adapter:
        async def send(self, email):
            sent.append(email.body)

    await Mailer(Adapter()).send("text")
    assert sent == ["text"]


@pytest.mark.asyncio
async def test_adapter_failure_propagates_to_caller():
    class Adapter:
        async def send(self, email):
            raise ConnectionError("offline")

    with pytest.raises(ConnectionError, match="offline"):
        await Mailer(Adapter()).send("text")


@pytest.mark.asyncio
async def test_missing_adapter_send_is_reported():
    with pytest.raises(NotImplementedError):
        await Mailer(object()).send("text")
