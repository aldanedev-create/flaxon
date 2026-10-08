

For generated projects, use the shared `settings.py`, `Flaxon.from_settings()`,
explicit mounts in `app.py`, and `management.py` workflow. See [ORM and project management](orm.md)
for Python migrations, model registration, permission hooks, relationship editing,
and Admin/CMS metadata storage. Backend-only and legacy adapter examples remain supported.
# Testing

## Overview

Flaxon provides comprehensive testing utilities including synchronous and asynchronous test clients, WebSocket testing, fixtures, database testing, authentication testing, mocking, and custom assertions.

## Installation

Install Flaxon with development dependencies:

```bash
pip install flaxon[dev]
````

---

# Basic Test Client

```python
from flaxon import Flaxon
from flaxon.testing import TestClient


def test_basic_route():

    app = Flaxon("test-app")

    @app.get("/")
    async def home():
        return {"message": "Hello"}

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello"
    }
```

---

# Async Test Client

```python
import pytest
from flaxon.testing import AsyncTestClient


@pytest.mark.asyncio
async def test_async_route():

    app = Flaxon("test-app")

    @app.get("/")
    async def home():
        return {"message": "Hello"}

    client = AsyncTestClient(app)

    response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello"
    }
```

---

# Testing HTTP Methods

```python
def test_all_methods():

    app = Flaxon("test-app")

    @app.get("/get")
    async def get_route():
        return {"method": "GET"}

    @app.post("/post")
    async def post_route():
        return {"method": "POST"}

    @app.put("/put")
    async def put_route():
        return {"method": "PUT"}

    @app.delete("/delete")
    async def delete_route():
        return {"method": "DELETE"}

    client = TestClient(app)

    assert client.get("/get").json()["method"] == "GET"
    assert client.post("/post").json()["method"] == "POST"
    assert client.put("/put").json()["method"] == "PUT"
    assert client.delete("/delete").json()["method"] == "DELETE"
```

---

# Testing Request Body

```python
def test_request_body():

    app = Flaxon("test-app")

    @app.post("/users")
    async def create_user(request):

        data = await request.json()

        return {
            "received": data
        }

    client = TestClient(app)

    response = client.post(
        "/users",
        json_data={
            "name": "Alice",
            "age": 30
        }
    )

    assert response.status_code == 200

    assert response.json()["received"] == {
        "name": "Alice",
        "age": 30
    }
```

---

# Testing Query Parameters

```python
def test_query_params():

    app = Flaxon("test-app")

    @app.get("/search")
    async def search(request):

        q = request.query.get("q")

        page = request.query.get_int(
            "page",
            1
        )

        return {
            "q": q,
            "page": page
        }


    client = TestClient(app)

    response = client.get(
        "/search",
        query={
            "q": "test",
            "page": 2
        }
    )


    assert response.json()["q"] == "test"
    assert response.json()["page"] == 2
```

---

# Testing Headers

```python
def test_headers():

    app = Flaxon("test-app")


    @app.get("/headers")
    async def headers(request):

        return {
            "user_agent": request.headers.get(
                "user-agent"
            )
        }


    client = TestClient(app)


    response = client.get(
        "/headers",
        headers={
            "User-Agent": "TestClient/1.0"
        }
    )


    assert response.json()["user_agent"] == "TestClient/1.0"
```

---

# Testing Cookies

```python
def test_cookies():

    app = Flaxon("test-app")


    @app.get("/cookies")
    async def cookies(request):

        return {
            "session": request.cookies.get(
                "session"
            )
        }


    client = TestClient(app)


    response = client.get(
        "/cookies",
        headers={
            "Cookie": "session=abc123"
        }
    )


    assert response.json()["session"] == "abc123"
```

---

# Testing Validation

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


def test_validation():

    app = Flaxon("test-app")


    @app.post("/users")
    async def create_user(data: CreateUser):

        return {
            "user": data.to_dict()
        }


    client = TestClient(app)


    response = client.post(
        "/users",
        json_data={
            "name": "Alice",
            "email": "alice@example.com"
        }
    )


    assert response.status_code == 200


    response = client.post(
        "/users",
        json_data={
            "name": "A",
            "email": "invalid"
        }
    )


    assert response.status_code == 422

    assert response.json()["error"]["code"] == "FX-VAL-001"
```

---

# Testing WebSockets

```python
import pytest

from flaxon import Flaxon
from flaxon.testing import AsyncWebSocketClient


@pytest.mark.asyncio
async def test_websocket():

    app = Flaxon("test-app")


    @app.websocket("/ws/echo")
    async def echo(socket):

        await socket.accept()

        async for message in socket.iter_json():

            await socket.send_json({
                "echo": message
            })


    client = AsyncWebSocketClient(app)


    await client.connect("/ws/echo")


    await client.send_json({
        "message": "Hello"
    })


    response = await client.receive_json()


    assert response == {
        "echo": {
            "message": "Hello"
        }
    }


    await client.disconnect()
```

---

# Testing With Fixtures

```python
import pytest

from flaxon import Flaxon
from flaxon.testing import TestClient


@pytest.fixture
def app():

    app = Flaxon("test-app")


    @app.get("/")
    async def home():

        return {
            "message": "Hello"
        }


    return app



@pytest.fixture
def client(app):

    return TestClient(app)



def test_with_fixtures(client):

    response = client.get("/")


    assert response.status_code == 200

    assert response.json() == {
        "message": "Hello"
    }
```

---

# Testing Database

```python
import pytest

from flaxon.database import DatabaseManager
from flaxon.database.adapters.sqlite import SQLiteAdapter


@pytest.fixture
async def db():

    adapter = SQLiteAdapter(
        database=":memory:"
    )

    manager = DatabaseManager(adapter)


    await manager.initialize()


    await manager.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)


    yield manager


    await manager.close()



@pytest.mark.asyncio
async def test_database(db):

    await db.execute(
        "INSERT INTO users(name) VALUES (?)",
        "Alice"
    )


    row = await db.fetch_one(
        "SELECT * FROM users WHERE name=?",
        "Alice"
    )


    assert row["name"] == "Alice"
```

---

# Testing Authentication

```python
from flaxon import Flaxon
from flaxon.testing import TestClient
from flaxon.security import JWTBackend


def test_authentication():

    app = Flaxon("test-app")

    backend = JWTBackend(
        secret_key="test-secret"
    )


    @app.post("/login")
    async def login(request):

        data = await request.json()

        token = await backend.create_token({
            "username": data["username"]
        })


        return {
            "token": token
        }



    client = TestClient(app)


    response = client.post(
        "/login",
        json_data={
            "username": "alice"
        }
    )


    token = response.json()["token"]


    response = client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
```

---

# Complete Test Example

```python
import pytest

from flaxon import Flaxon, HTTPException
from flaxon.testing import TestClient


app = Flaxon("test-app")

users = []


@app.get("/")
async def home():

    return {
        "message": "Welcome"
    }


@app.get("/users")
async def list_users():

    return users



@app.post("/users")
async def create_user(request):

    data = await request.json()

    user = {
        "id": len(users) + 1,
        **data
    }

    users.append(user)

    return {
        "created": True,
        "user": user
    }



@app.get("/users/<int:user_id>")
async def get_user(user_id):

    for user in users:

        if user["id"] == user_id:

            return user


    raise HTTPException(
        404,
        "User not found"
    )



@pytest.fixture
def client():

    return TestClient(app)



def test_home(client):

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["message"] == "Welcome"



def test_create_user(client):

    response = client.post(
        "/users",
        json_data={
            "name": "Alice"
        }
    )


    assert response.status_code == 200

    assert response.json()["created"] is True
```

---

# Testing Best Practices

* Test every route.
* Test successful responses.
* Test validation errors.
* Test authentication failures.
* Test database operations separately.
* Use fixtures for reusable setup.
* Mock external services.
* Test WebSocket connections.
* Test background tasks.
* Run tests automatically in CI/CD.

---

# Running Tests

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=flaxon
```

Run async tests:

```bash
pytest -asyncio
```

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
