from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass, field
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import Any


@dataclass
class EmailAddress:
    address: str
    name: str | None = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address

    def to_tuple(self) -> tuple[str, str]:
        return (self.address, self.name or "")


@dataclass
class Attachment:
    filename: str
    content: bytes
    content_type: str | None = None

    def __post_init__(self) -> None:
        if self.content_type is None:
            guessed = mimetypes.guess_type(self.filename)[0]
            self.content_type = guessed or "application/octet-stream"


@dataclass
class Email:
    from_address: EmailAddress | str
    to: list[EmailAddress | str] = field(default_factory=list)
    cc: list[EmailAddress | str] = field(default_factory=list)
    bcc: list[EmailAddress | str] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    html_body: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    reply_to: EmailAddress | str | None = None

    def __post_init__(self) -> None:
        self.to = self._normalize_addresses(self.to)
        self.cc = self._normalize_addresses(self.cc)
        self.bcc = self._normalize_addresses(self.bcc)
        if self.reply_to:
            self.reply_to = self._normalize_address(self.reply_to)

    def _normalize_address(self, address: EmailAddress | str) -> EmailAddress:
        if isinstance(address, str):
            return EmailAddress(address)
        return address

    def _normalize_addresses(self, addresses: list[EmailAddress | str]) -> list[EmailAddress]:
        return [self._normalize_address(addr) for addr in addresses]

    def to_mime(self) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")

        msg["Subject"] = self.subject
        msg["From"] = (
            str(self.from_address) if isinstance(self.from_address, EmailAddress) else self.from_address
        )
        msg["To"] = ", ".join(str(addr) for addr in self.to)
        msg["Date"] = formatdate()

        if self.cc:
            msg["Cc"] = ", ".join(str(addr) for addr in self.cc)

        if self.reply_to:
            msg["Reply-To"] = str(self.reply_to)

        for key, value in self.headers.items():
            msg[key] = value

        if self.html_body:
            text_part = MIMEText(self.body, "plain", "utf-8")
            html_part = MIMEText(self.html_body, "html", "utf-8")
            msg.attach(text_part)
            msg.attach(html_part)
        else:
            msg.attach(MIMEText(self.body, "plain", "utf-8"))

        for attachment in self.attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.content)
            part.add_header("Content-Disposition", f'attachment; filename="{attachment.filename}"')
            part.add_header("Content-Transfer-Encoding", "base64")
            msg.attach(part)

        return msg

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": str(self.from_address),
            "to": [str(addr) for addr in self.to],
            "cc": [str(addr) for addr in self.cc],
            "bcc": [str(addr) for addr in self.bcc],
            "subject": self.subject,
            "body": self.body,
            "html_body": self.html_body,
            "attachments": [a.filename for a in self.attachments],
        }


class Message:
    def __init__(self) -> None:
        self.email = Email(from_address="", to=[])

    def from_address(self, address: str, name: str | None = None) -> Message:
        self.email.from_address = EmailAddress(address, name)
        return self

    def to(self, *addresses: str | tuple[str, str]) -> Message:
        for addr in addresses:
            if isinstance(addr, tuple):
                self.email.to.append(EmailAddress(addr[0], addr[1]))
            else:
                self.email.to.append(EmailAddress(addr))
        return self

    def cc(self, *addresses: str | tuple[str, str]) -> Message:
        for addr in addresses:
            if isinstance(addr, tuple):
                self.email.cc.append(EmailAddress(addr[0], addr[1]))
            else:
                self.email.cc.append(EmailAddress(addr))
        return self

    def bcc(self, *addresses: str | tuple[str, str]) -> Message:
        for addr in addresses:
            if isinstance(addr, tuple):
                self.email.bcc.append(EmailAddress(addr[0], addr[1]))
            else:
                self.email.bcc.append(EmailAddress(addr))
        return self

    def subject(self, subject: str) -> Message:
        self.email.subject = subject
        return self

    def body(self, body: str) -> Message:
        self.email.body = body
        return self

    def html(self, html: str) -> Message:
        self.email.html_body = html
        return self

    def attach(
        self, filename: str, content: bytes | str | None = None, content_type: str | None = None
    ) -> Message:
        if content is None:
            with open(filename, "rb") as f:
                content = f.read()
                filename = os.path.basename(filename)

        if isinstance(content, str):
            content = content.encode("utf-8")

        self.email.attachments.append(Attachment(filename, content, content_type))
        return self

    def reply_to(self, address: str, name: str | None = None) -> Message:
        self.email.reply_to = EmailAddress(address, name)
        return self

    def header(self, key: str, value: str) -> Message:
        self.email.headers[key] = value
        return self

    def build(self) -> Email:
        return self.email
