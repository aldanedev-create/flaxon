from __future__ import annotations

import smtplib

from flaxon.mail.message import Email


class SMTPAdapter:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: int = 30,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout

    async def send(self, email: Email) -> None:
        msg = email.to_mime()

        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

        try:
            if not self.use_ssl and self.use_tls:
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            from_address = str(email.from_address)
            to_addresses = [str(addr) for addr in email.to]

            if email.cc:
                to_addresses.extend(str(addr) for addr in email.cc)
            if email.bcc:
                to_addresses.extend(str(addr) for addr in email.bcc)

            server.sendmail(from_address, to_addresses, msg.as_string())

        finally:
            server.quit()
