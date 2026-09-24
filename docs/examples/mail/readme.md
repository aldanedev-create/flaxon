# Mail Example

This is a complete, same-origin contact form. The app serves the HTML page at
`/` and posts validated data to `/api/contact`.

## Run it

From the repository root:

```bash
python -m pip install -e .
flaxon run docs.examples.mail.app:app --reload
```

Open <http://127.0.0.1:8000/>. By default, `ConsoleAdapter` prints the email
to the terminal and does not contact an SMTP server.

## Use SMTP

Set these variables before starting the server. Credentials stay outside the
source code:

```bash
FLAXON_SMTP_HOST=smtp.example.com
FLAXON_SMTP_PORT=587
FLAXON_SMTP_USERNAME=mailer@example.com
FLAXON_SMTP_PASSWORD=replace-me
FLAXON_SMTP_TLS=true
FLAXON_MAIL_FROM=noreply@example.com
FLAXON_MAIL_TO=support@example.com
```

The app switches to `SMTPAdapter` when `FLAXON_SMTP_HOST` is present. Use
`FLAXON_SMTP_SSL=true` for implicit TLS, normally on port 465, and do not use
implicit SSL and STARTTLS for the same connection.

The example uses `EmailField` and length limits before sending. For production,
add authentication or abuse protection to public contact forms and use a task
queue for slow or high-volume delivery. See the full [Mail guide](../../mail.md).
