

For generated projects, use the shared `settings.py`, `Flaxon.from_settings()`,
explicit mounts in `app.py`, and `management.py` workflow. See [ORM and project management](guides/orm.md)
for Python migrations, model registration, permission hooks, relationship editing,
and Admin/CMS metadata storage. Backend-only and legacy adapter examples remain supported.
# Security

## Overview

Security is an important part of Flaxon's design.

Flaxon provides secure defaults and documentation to help developers build safer applications.

The framework includes support for:

- Template autoescaping
- Request validation
- Security headers
- Request identifiers
- Sensitive data redaction
- Production-safe error handling
- Rate limiting

Security features reduce common risks, but developers are still responsible for following secure application practices.

---

# Built-in Security Features

## Autoescaping

Jinax templates automatically escape HTML and XML content to help prevent Cross-Site Scripting (XSS) attacks.

Example:

```html
{{ user_input }}
````

Unsafe characters are escaped before being rendered.

---

# Request Validation

Flaxon supports declarative schemas for validating incoming data before processing.

Example:

```python
from flaxon.validation import Schema, fields


class CreateUser(Schema):

    name = fields.StrField(
        required=True,
        min_length=2
    )

    email = fields.EmailField(
        required=True
    )
```

Validation helps prevent malformed or unexpected input from reaching application logic.

---

# Security Headers

Flaxon can apply recommended security headers.

Common headers include:

```
X-Content-Type-Options: nosniff

X-Frame-Options: DENY

Referrer-Policy: strict-origin-when-cross-origin

Permissions-Policy:
geolocation=(),
microphone=(),
camera=()
```

These headers help protect against:

* Content type attacks
* Clickjacking
* Unnecessary browser permissions

---

# Request IDs

Every request can receive a unique identifier.

Request IDs help with:

* Debugging
* Logging
* Distributed tracing
* Production troubleshooting

Example:

```
Request-ID: fx-8a72c91d
```

---

# Sensitive Data Redaction

Flaxon avoids exposing sensitive information in logs and debug output.

Sensitive values should be protected, including:

* Passwords
* Secrets
* Authentication tokens
* API keys
* Private keys
* Credit card information
* Authorization headers

---

# Production-Safe Errors

In production mode, Flaxon returns safe error responses.

Production errors should:

* Hide internal tracebacks
* Avoid exposing application details
* Provide useful error identifiers

Detailed debugging information should only be enabled in development environments.

---

# Rate Limiting

Rate limiting helps prevent abuse by restricting excessive requests.

Use cases include:

* API protection
* Login protection
* Resource management
* Abuse prevention

---

# Security Recommendations

## Admin and CMS Hardening

For Admin deployments, configure a shared Redis backend for sessions and
distributed request limits, keep CSRF enabled, and use `session_idle_timeout`
with HTTPS-only deployment. Password-reset and MFA operations are separately
limited by account and IP when Redis is configured.

Media uploads can use a scanner callback, SHA-256 metadata, EXIF removal, and
S3 presigned URLs. A scanner callback is only production antivirus protection
when connected to an actual engine such as ClamAV; returning `True` from a test
callback does not scan files.

Audit records are hash chained and can be checked with
`GET /admin/audit/verify`. Keep audit storage append-only at the database and
infrastructure layers, and define a retention policy before deployment.

## Production Checklist

Before deploying a Flaxon application:

* [ ] Set `FLAXON_DEBUG=false`
* [ ] Set `FLAXON_SECRET_KEY` with 32+ random bytes
* [ ] Configure `FLAXON_ALLOWED_HOSTS`
* [ ] Enable HTTPS
* [ ] Use secure cookies:

  * `Secure`
  * `HttpOnly`
  * `SameSite`
* [ ] Implement authentication and authorization
* [ ] Enable rate limiting
* [ ] Validate all user input
* [ ] Use parameterized database queries
* [ ] Keep dependencies updated
* [ ] Scan dependencies for vulnerabilities

---

# Authentication

Flaxon supports authentication backends for securing protected routes.

Example:

```python
from flaxon.security import JWTBackend, login_required


app = Flaxon(
    "secure-app"
)


backend = JWTBackend(
    secret_key="your-secret"
)


@app.post("/login")
async def login(request):

    user = await authenticate_user(
        data
    )

    token = await backend.create_token(
        user
    )

    return {
        "token": token
    }


@app.get("/protected")
@login_required
async def protected(request):

    user = getattr(
        request,
        "user",
        None
    )

    return {
        "user": user.to_dict()
    }
```

---

# CSRF Protection

For applications using cookies and browser sessions, enable CSRF protection.

Example:

```python
from flaxon.security import CSRFMiddleware


app.add_middleware(
    CSRFMiddleware,
    secret_key="your-secret"
)
```

---

# CORS Configuration

Configure Cross-Origin Resource Sharing (CORS) carefully.

Example:

```python
from flaxon.middleware import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allowed_origins=[
        "https://example.com"
    ],
    allow_credentials=True
)
```

Avoid allowing unrestricted origins in production environments.

---

# Rate Limiting Configuration

Example:

```python
from flaxon.security import RateLimitMiddleware


app.add_middleware(
    RateLimitMiddleware,
    requests=60,
    window_seconds=60
)
```

---

# Threat Mitigation

| Threat               | Control                                    |
| -------------------- | ------------------------------------------ |
| XSS                  | Template escaping, Content Security Policy |
| SQL Injection        | Parameterized queries, validation          |
| Credential Theft     | Secure password hashing, MFA               |
| Token Abuse          | Short-lived tokens, refresh rotation       |
| CSRF                 | CSRF tokens                                |
| DDoS                 | Rate limiting, timeouts                    |
| Data Leakage         | Redaction, safe error handling             |
| Supply Chain Attacks | Dependency pinning, security scanning      |

---

# Reporting Vulnerabilities

If you discover a security vulnerability in Flaxon:

Please report it responsibly.

Contact:

`aldanehutchinson5@gmail.com`

or create a private security advisory through the Flaxon GitHub repository.

Please do not publicly disclose security issues before they are reviewed and addressed.


## Authentication and session migration

See [request security upgrades](guides/request-security-upgrade.md) for standard JWTs, Argon2 upgrades, typed query validation and lazy session creation.
