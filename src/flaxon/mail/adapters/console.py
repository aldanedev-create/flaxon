from __future__ import annotations

from datetime import datetime

from flaxon.mail.message import Email


class ConsoleAdapter:
    """Console adapter implementation for the mail subsystem."""

    def __init__(self, print_body: bool = True, print_html: bool = False) -> None:
        self.print_body = print_body
        self.print_html = print_html

    async def send(self, email: Email) -> None:
        """Perform the send operation for console adapter."""
        print("=" * 60)
        print(f"[{datetime.now().isoformat()}] Email sent")
        print(f"From: {email.from_address}")
        print(f"To: {', '.join(str(addr) for addr in email.to)}")
        if email.cc:
            print(f"Cc: {', '.join(str(addr) for addr in email.cc)}")
        if email.bcc:
            print(f"Bcc: {', '.join(str(addr) for addr in email.bcc)}")
        print(f"Subject: {email.subject}")

        if email.headers:
            print("Headers:")
            for key, value in email.headers.items():
                print(f"  {key}: {value}")

        if self.print_body:
            print("Body:")
            print(email.body)
            print("-" * 40)

        if self.print_html and email.html_body:
            print("HTML Body:")
            print(email.html_body)
            print("-" * 40)

        if email.attachments:
            print("Attachments:")
            for attachment in email.attachments:
                print(f"  - {attachment.filename} ({len(attachment.content)} bytes)")

        print("=" * 60)
