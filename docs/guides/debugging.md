
# Debugging

## Overview

Flaxon includes a built-in debugging system designed to help developers identify and fix application issues quickly.

The debugger provides:

- Clear error explanations
- Error codes
- Request context
- Stack traces during development
- Recorded application errors
- Issue history
- Sensitive data redaction
- Debugging information through a web interface

Flaxon's goal is to make debugging easier by explaining **what happened, why it happened, and where to fix it**.

---

# Debug Mode

Debug mode enables detailed error reporting and the debugging dashboard.

## Enabling Debug Mode

### Using Application Configuration

```python
from flaxon import Flaxon


app = Flaxon(
    "my-app",
    debug=True
)
````

---

### Using Configuration Options

```python
from flaxon import Flaxon


app = Flaxon(
    "my-app",
    config={
        "DEBUG": True
    }
)
```

---

# Debug Dashboard

When debug mode is enabled, Flaxon provides a local debugging dashboard.

Open:

```
http://localhost:8000/__debug__
```

The dashboard displays:

* Recorded errors
* Application exceptions
* Request information
* Error timestamps
* Error frequency
* Stack traces
* Error codes
* Debug logs

Example:

```
Flaxon Debug Dashboard

Application:
my-app

Status:
Development Mode


Recent Errors:

[FX-404]
RouteNotFoundError

Time:
2026-08-03 10:30:15


[FX-500]
DatabaseConnectionError

Time:
2026-08-03 10:32:04
```

---

# Error Recording

Flaxon automatically records errors during development.

Each error entry contains:

| Field       | Description                    |
| ----------- | ------------------------------ |
| Error Code  | Unique Flaxon error identifier |
| Type        | Exception class                |
| Message     | Human-readable explanation     |
| Time        | When the error occurred        |
| Route       | Request path                   |
| Method      | HTTP method                    |
| Request ID  | Trace identifier               |
| Stack Trace | Debug traceback                |

---

# Error Codes

Flaxon uses structured error codes to make issues easier to identify.

Example:

```python
raise HTTPException(
    404,
    "User not found",
    code="FX-USER-404"
)
```

Example codes:

| Code   | Meaning                    |
| ------ | -------------------------- |
| FX-404 | Resource not found         |
| FX-401 | Authentication failure     |
| FX-403 | Permission denied          |
| FX-422 | Validation failure         |
| FX-500 | Internal application error |

---

# Request Context

The debugger includes useful request information:

Example:

```
Request

Method:
POST

Path:
/api/users

Request ID:
fx-a82c91

IP:
127.0.0.1

Headers:
Content-Type: application/json
```

Sensitive values are automatically hidden.

---

# Sensitive Data Protection

The debugger removes sensitive information from logs.

Protected values include:

* Passwords
* Authentication tokens
* API keys
* Secrets
* Private keys
* Authorization headers
* Payment information

Example:

Before:

```
password=myPassword123
```

After:

```
password=[REDACTED]
```

---

# Debugging Exceptions

Example:

```python
@app.get("/users/<int:user_id>")
async def get_user(user_id: int):

    user = await database.find_user(
        user_id
    )

    return user.name
```

If `user` is missing, the debugger provides:

```
Error:
AttributeError

Message:
User object is None

Location:
app.py line 12

Suggestion:
Check if the database query returned a valid user.
```

---

# Clearing Debug Records

During development, stored errors can be cleared.

Example:

```bash
flaxon debug clear
```

---

# Production Safety

Debug mode should never be enabled in production.

Disable:

```python
app = Flaxon(
    "my-app",
    debug=False
)
```

Production mode:

* Hides stack traces
* Returns safe error messages
* Prevents debug dashboard access
* Protects sensitive information

---

# Debugging Workflow

Recommended workflow:

1. Enable debug mode.

```python
app = Flaxon(
    "my-app",
    debug=True
)
```

2. Start the application.

```bash
flaxon run app:app --reload
```

3. Open:

```
http://localhost:8000/__debug__
```

4. Review recorded errors.

5. Fix the issue.

6. Restart the application.

---

# Best Practices

For effective debugging:

* Use meaningful error codes.
* Include request IDs in logs.
* Keep debug mode limited to development.
* Never expose debug dashboards publicly.
* Review logs before deploying.
* Use monitoring tools for production systems.

---

# Next Steps

Related documentation:

* Security
* Performance
* Configuration
* Architecture


## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
