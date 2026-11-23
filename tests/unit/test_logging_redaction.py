"""Structured log formatters must redact secrets/PII before emitting JSON."""

from __future__ import annotations

import json
import logging

from flaxon.logging.formatters import AuditFormatter, JSONFormatter


def _record(**extra):
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="x.py",
        lineno=1,
        msg="event",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_redacts_sensitive_extra_fields():
    record = _record(
        extra={
            "username": "alice",
            "password": "hunter2-super-secret",
            "token": "eyJhbGciOiJIUzI1NiJ9.payload",
            "note": "contact me at alice@example.com",
        }
    )
    output = JSONFormatter().format(record)
    data = json.loads(output)
    assert data["password"] == "[REDACTED]"
    assert data["token"] == "[REDACTED]"
    assert "alice@example.com" not in output
    assert data["username"] == "alice"


def test_audit_formatter_redacts_changes_and_includes_outcome():
    record = _record(
        action="create",
        resource="user",
        changes={"username": "bob", "password": "plaintext-password"},
        ip="1.2.3.4",
        user_agent="curl",
        status="success",
        error=None,
    )
    output = AuditFormatter().format(record)
    data = json.loads(output)
    assert data["changes"]["password"] == "[REDACTED]"
    assert data["changes"]["username"] == "bob"
    assert data["status"] == "success"
