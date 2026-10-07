"""Mail mime content behavior and boundary cases."""

from flaxon.mail.message import Email, Message


def test_html_and_plain_text_alternatives_keep_unicode():
    email = Email(
        "sender@example.com", ["to@example.com"], subject="Hello", body="Zoë", html_body="<p>Zoë</p>"
    )
    parts = email.to_mime().get_payload()
    assert [part.get_content_type() for part in parts] == ["text/plain", "text/html"]
    assert parts[0].get_payload(decode=True).decode() == "Zoë"
    assert parts[1].get_payload(decode=True).decode() == "<p>Zoë</p>"


def test_bcc_recipients_are_not_exposed_in_mime_headers():
    email = Email(
        "sender@example.com", ["to@example.com"], cc=["cc@example.com"], bcc=["private@example.com"]
    )
    mime = email.to_mime()
    assert mime["Bcc"] is None and "private@example.com" not in mime.as_string()
    assert "cc@example.com" in mime["Cc"]


def test_builder_retains_named_recipients_and_reply_address():
    email = (
        Message()
        .from_address("sender@example.com", "Sender")
        .to(("to@example.com", "Recipient"))
        .reply_to("reply@example.com")
        .subject("Hello")
        .body("Text")
        .build()
    )
    assert str(email.to[0]) == "Recipient <to@example.com>"
    assert email.to_mime()["Reply-To"] == "reply@example.com"
