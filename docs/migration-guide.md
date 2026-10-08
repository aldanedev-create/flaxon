

For generated projects, use the shared `settings.py`, `Flaxon.from_settings()`,
explicit mounts in `app.py`, and `management.py` workflow. See [ORM and project management](guides/orm.md)
for Python migrations, model registration, permission hooks, relationship editing,
and Admin/CMS metadata storage. Backend-only and legacy adapter examples remain supported.


# Migration Guide

This guide helps developers migrate existing applications from popular Python frameworks to **Flaxon**.

Flaxon provides a modern, async-first approach while keeping familiar patterns from frameworks like Flask, Django, and FastAPI.

---

# Migrating from Flask

## Route Decorators

### Flask

```python
@app.route("/users/<int:user_id>")
def get_user(user_id):
    return jsonify({"id": user_id})
````

### Flaxon

```python
@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {"id": user_id}
```

---

## Request and Response

### Flask

```python
data = request.get_json()

return jsonify({
    "status": "ok"
})
```

### Flaxon

```python
data = await request.json()

return {
    "status": "ok"
}
```

---

## Validation

### Flask

Flask usually requires manual validation:

```python
if not username:
    return {"error": "Username required"}
```

### Flaxon

Flaxon provides schema-based validation:

```python
class CreateUser(Schema):
    name = fields.StrField(required=True)
```

---

## WebSockets

### Flask

Requires an additional extension:

```python
# Requires Flask-SocketIO
```

### Flaxon

Built-in async WebSocket support:

```python
@app.websocket("/ws/chat")
async def chat(socket):
    await socket.accept()
```

---

# Migrating from Django

## Views

### Django

```python
def get_user(request, user_id):
    return JsonResponse({
        "id": user_id
    })
```

### Flaxon

```python
@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {
        "id": user_id
    }
```

---

## Serializers

### Django REST Framework

```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name"
        ]
```

### Flaxon

```python
class UserSchema(Schema):
    id = fields.IntField()
    name = fields.StrField()
```

---

# Migrating from FastAPI

## Path Parameters

### FastAPI

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {
        "id": user_id
    }
```

### Flaxon

```python
@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {
        "id": user_id
    }
```

---

## Validation

### FastAPI

```python
class User(BaseModel):
    name: str
    email: EmailStr
```

### Flaxon

```python
class User(Schema):
    name = fields.StrField(required=True)
    email = fields.EmailField(required=True)
```

---

# Common Patterns

## Database Connection

### Flaxon Startup and Shutdown

```python
@app.on_startup
async def startup():
    app.state.db = await create_pool()


@app.on_shutdown
async def shutdown():
    await app.state.db.close()
```

---

# Dependency Injection

Flaxon supports dependency injection for managing application services.

```python
from flaxon.dependency_injection import Container, inject


container = Container()

container.register_instance(
    "db",
    db_pool
)


@inject(container)
async def get_users(db):
    return await db.fetch_all(
        "SELECT * FROM users"
    )
```

---

# Testing

Flaxon provides a testing client for application testing.

```python
from flaxon.testing import TestClient


def test_get_users():
    client = TestClient(app)

    response = client.get("/users")

    assert response.status_code == 200
```

---

# Breaking Changes

## Version 0.1.0 → Future Versions

Before Flaxon reaches version `1.0`, some APIs may change.

Migration notes:

* Check `CHANGELOG.md` before upgrading.
* Follow semantic versioning.
* Review deprecated features before updating.

---

# Getting Help

If you need help migrating:

## GitHub Issues

Report bugs or migration problems through GitHub Issues.

## Discussions

Ask questions and share migration tips through GitHub Discussions.

```
