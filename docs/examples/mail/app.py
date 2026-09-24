"""Runnable contact form using Flaxon's mail adapters.

Run locally with the console adapter:

    flaxon run docs.examples.mail.app:app --reload

Set ``FLAXON_SMTP_HOST`` and the other documented variables to switch to
SMTP. The example intentionally defaults to console output so it never sends
real mail by accident during development.
"""

from __future__ import annotations

import os
from pathlib import Path

from flaxon import Flaxon
from flaxon.http import HTMLResponse, JSONResponse
from flaxon.mail import Mailer, Message
from flaxon.mail.adapters.console import ConsoleAdapter
from flaxon.mail.adapters.smtp import SMTPAdapter
from flaxon.validation import Schema, fields

BASE_DIR = Path(__file__).parent
app = Flaxon("mail-example", debug=True)


def build_mailer() -> Mailer:
    smtp_host = os.getenv("FLAXON_SMTP_HOST")
    if not smtp_host:
        return Mailer(ConsoleAdapter(print_body=True))

    use_ssl = os.getenv("FLAXON_SMTP_SSL", "false").lower() == "true"
    return Mailer(
        SMTPAdapter(
            host=smtp_host,
            port=int(os.getenv("FLAXON_SMTP_PORT", "587")),
            username=os.getenv("FLAXON_SMTP_USERNAME"),
            password=os.getenv("FLAXON_SMTP_PASSWORD"),
            use_tls=os.getenv(
                "FLAXON_SMTP_TLS", "false" if use_ssl else "true"
            ).lower() == "true",
            use_ssl=use_ssl,
        )
    )


mailer = build_mailer()


class ContactForm(Schema):
    name = fields.StrField(required=True, min_length=1, max_length=120)
    email = fields.EmailField(required=True)
    message = fields.StrField(required=True, min_length=1, max_length=2000)


@app.get("/")
async def contact_page() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/api/contact")
async def send_contact_email(data: ContactForm) -> JSONResponse:
    from_address = os.getenv("FLAXON_MAIL_FROM", "noreply@example.com")
    support_address = os.getenv("FLAXON_MAIL_TO", "support@example.com")
    email = (
        Message()
        .from_address(from_address, "Flaxon Example")
        .to(support_address)
        .reply_to(data.email, data.name)
        .subject(f"New contact form message from {data.name}")
        .body(f"From: {data.name} <{data.email}>\n\n{data.message}")
        .build()
    )
    await mailer.send(email)
    return JSONResponse({"sent": True}, status_code=201)
