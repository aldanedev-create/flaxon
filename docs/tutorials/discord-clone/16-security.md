# Lesson 16: Security review

Before running in front of real users, walk the boundaries the course built. Each
is a property, not a checkbox — and each is pinned by a test.

- **Passwords** — hashed with argon2 (`flaxon.security.password`); the plaintext
  never leaves `register_user`. *Test:* `register` with a short password → `400`.
- **CSRF** — every mutation carries `require_csrf`; a missing or invalid token is
  `403 Forbidden`. *Test:* `tests/test_security.py::test_invalid_csrf_is_rejected`.
- **Generic auth errors** — login never reveals whether a username exists
  (`401` with one message). *Test:* `test_wrong_password_does_not_reveal_account`.
- **Private channels** — isolation is enforced in the database via
  `ChannelAccess`, not only hidden in the UI. *Test:*
  `test_private_channel_hidden_from_unauthorized_member`.
- **Bot tokens** — stored only as a SHA-256 hash; the plaintext is shown once and
  never persisted. *Test:* `test_token_is_hashed_not_stored_plaintext`.
- **No untrusted code** — bot behaviour is a set of registered handlers; no
  arbitrary Python runs in the web process.
- **Rate limiting** — login/register/server-create/bot-create are bucketed per
  client IP; it is process-local and disabled in tests via
  `RATE_LIMIT_ENABLED=false`.
- **Secrets** — `SECRET_KEY` and `DATABASE_URL` come from `.env`; nothing
  sensitive is committed.

**Checkpoint:** read `modules/_common.py` and `context.py` end to end. Every
mutating route passes through `require_csrf`; every resource route passes through
`authorize_server`/`authorize_channel`. If you ever add an endpoint that skips
either, you have introduced a vulnerability — keep the helpers as the only path.
