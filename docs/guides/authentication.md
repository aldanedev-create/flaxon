
# Authentication

## Overview

Flaxon provides flexible authentication support through pluggable authentication backends.

Supported approaches include:

- JWT authentication
- Session-based authentication
- API key authentication
- OAuth2 providers
- Custom authentication implementations

Flaxon does not force a single authentication strategy. Developers can choose the approach that best fits their application.

---

# JWT Authentication

JWT (JSON Web Token) authentication is commonly used for APIs, mobile applications, and distributed systems.

---

## Setup

```python
from flaxon import Flaxon
from flaxon.security import (
    JWTBackend,
    AuthenticationMiddleware,
    login_required
)


app = Flaxon(
    "auth-app"
)


backend = JWTBackend(
    secret_key="your-secret-key"
)


app.add_middleware(
    AuthenticationMiddleware,
    backend=backend
)
````

---

# Login

Create a login endpoint that validates credentials and returns a token.

```python
from flaxon.security import User


@app.post("/login")
async def login(request):

    data = await request.json()


    user = await authenticate_user(
        data["username"],
        data["password"]
    )


    if not user:
        raise HTTPException(
            401,
            "Invalid credentials"
        )


    token = await backend.create_token(
        user
    )


    return {
        "token": token,
        "user": user.to_dict()
    }
```

---

# Protecting Routes

Use `login_required` to protect authenticated endpoints.

```python
@app.get("/profile")
@login_required
async def profile(request):

    user = getattr(
        request,
        "user"
    )


    return {
        "user": user.to_dict()
    }
```

---

# Custom User Model

Applications can extend the default user model with custom fields and permissions.

```python
from flaxon.security import User


class CustomUser(User):

    def __init__(
        self,
        id,
        username,
        email,
        roles=None
    ):

        super().__init__(
            id,
            username,
            email,
            roles
        )


        self.permissions = [
            "read",
            "write"
        ]


    def can_access_admin(self):

        return "admin" in self.roles
```

---

# Session Authentication

Session authentication is useful for traditional web applications.

Example:

```python
from flaxon.security import (
    SessionBackend,
    AuthenticationMiddleware
)


backend = SessionBackend()


app.add_middleware(
    AuthenticationMiddleware,
    backend=backend
)


@app.post("/login")
async def login(request):

    user = await authenticate_user(
        data
    )


    session_id = await backend.create_token(
        user
    )


    response = JSONResponse(
        {
            "success": True
        }
    )


    response.headers["set-cookie"] = (
        f"session_id={session_id}; "
        "HttpOnly; Path=/"
    )


    return response
```

---

# API Key Authentication

API keys are useful for service-to-service communication and external integrations.

```python
from flaxon.security import (
    APIKeyManager,
    api_key_required
)


manager = APIKeyManager()


key, hashed = manager.generate_key()


manager.register(
    key
)


app.state.api_key_manager = manager


@app.get("/protected")
@api_key_required
async def protected(request):

    return {
        "data": "secret"
    }
```

---

# OAuth2 protocol helpers

Flaxon provides configurable OAuth2 protocol helpers for authorization URL
creation and authorization-code/token refresh requests. They do not create
login routes, validate callback state, provision users, or establish an
application session automatically. Your application must implement those
steps, or use a dedicated identity provider integration.

Example:

```python
from flaxon.security import (
    OAuth2Provider,
    OAuth2Backend
)


provider = OAuth2Provider(

    client_id="your-client-id",

    client_secret="your-client-secret",

    authorization_endpoint=(
        "https://auth.example.com/authorize"
    ),

    token_endpoint=(
        "https://auth.example.com/token"
    ),

    redirect_uri=(
        "https://your-app.com/callback"
    )
)


backend = OAuth2Backend()


backend.register_provider(
    "example",
    provider
)


@app.get("/auth/login")
async def auth_login():

    url = backend.get_authorization_url(
        "example"
    )

    return RedirectResponse(url)


@app.get("/auth/callback")
async def auth_callback(request):

    code = request.query.get(
        "code"
    )


    user_data = await backend.authenticate(
        "example",
        code
    )


    return {
        "user": user_data
    }
```

---

# Password Hashing

Passwords should never be stored as plain text.

Flaxon provides password hashing utilities.

```python
from flaxon.security import (
    hash_password,
    verify_password
)


hashed = hash_password(
    "my-password"
)


is_valid = verify_password(
    "my-password",
    hashed
)


if needs_rehash(hashed):

    hashed = hash_password(
        "my-password"
    )
```

---

# Complete Authentication Example

Example API with registration, login, and protected routes.

```python
from flaxon import (
    Flaxon,
    HTTPException
)

from flaxon.security import (
    JWTBackend,
    AuthenticationMiddleware,
    login_required,
    User,
    hash_password,
    verify_password,
)


app = Flaxon(
    "auth-demo"
)


backend = JWTBackend(
    secret_key="your-secret-key"
)


app.add_middleware(
    AuthenticationMiddleware,
    backend=backend
)


# Example storage
# Use a database in production

users = {}


@app.post("/register")
async def register(request):

    data = await request.json()


    if data["username"] in users:

        raise HTTPException(
            400,
            "Username already exists"
        )


    user = User(

        id=len(users) + 1,

        username=data["username"],

        email=data["email"],

        roles=[
            "user"
        ]
    )


    users[data["username"]] = {

        "user": user,

        "password": hash_password(
            data["password"]
        )
    }


    return {

        "success": True,

        "user": user.to_dict()

    }



@app.post("/login")
async def login(request):

    data = await request.json()


    stored = users.get(
        data["username"]
    )


    if not stored:

        raise HTTPException(
            401,
            "Invalid credentials"
        )


    if not verify_password(
        data["password"],
        stored["password"]
    ):

        raise HTTPException(
            401,
            "Invalid credentials"
        )


    token = await backend.create_token(
        stored["user"]
    )


    return {
        "token": token
    }



@app.get("/profile")
@login_required
async def profile(request):

    user = getattr(
        request,
        "user"
    )


    return {
        "user": user.to_dict()
    }



@app.get("/admin")
@login_required
async def admin(request):

    user = getattr(
        request,
        "user"
    )


    if "admin" not in user.roles:

        raise HTTPException(
            403,
            "Admin access required"
        )


    return {
        "admin": True
    }
```

---

# Security Recommendations

For production applications:

* Store users in a database.
* Use strong secret keys.
* Enable HTTPS.
* Rotate tokens when appropriate.
* Use short-lived access tokens.
* Protect sensitive routes with authorization checks.
* Never store plain-text passwords.
* Apply rate limiting to login endpoints.

---

# Next Steps

Related documentation:

* Security Guide
* Middleware
* Authorization
* API Development

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
