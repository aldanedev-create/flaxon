# Authorization

## Overview

Flaxon provides flexible authorization through roles, permissions, decorators, and utility classes. Authorization is separate from authentication, allowing you to choose the strategy that best fits your application.

Authentication answers **who the user is**.

Authorization answers **what the user is allowed to do**.

---

# Role-Based Authorization

Roles group related permissions together.

## Registering Roles

```python
from flaxon.security import register_role

register_role(
    name="admin",
    permissions=[
        "read",
        "write",
        "delete",
        "manage_users",
    ],
    description="Administrator",
)

register_role(
    name="moderator",
    permissions=[
        "read",
        "write",
        "delete",
    ],
)

register_role(
    name="user",
    permissions=[
        "read",
    ],
)
```

---

## Role Inheritance

Roles may inherit permissions from another role.

```python
from flaxon.security import register_role

user = register_role(
    name="user",
    permissions=["read"],
)

moderator = register_role(
    name="moderator",
    permissions=[
        "write",
        "delete",
    ],
    parent=user,
)

admin = register_role(
    name="admin",
    permissions=[
        "manage_users",
    ],
    parent=moderator,
)
```

The resulting permissions become:

| Role | Permissions |
|------|-------------|
| User | read |
| Moderator | read, write, delete |
| Admin | read, write, delete, manage_users |

---

# Permission-Based Authorization

Permissions can also be assigned directly.

```python
from flaxon.security import (
    register_permission,
    permission_required,
)

register_permission(
    "read",
    "Read data",
)

register_permission(
    "write",
    "Write data",
)

register_permission(
    "delete",
    "Delete data",
)
```

Protect routes with decorators.

```python
@app.get("/users")
@permission_required("read")
async def users():
    return []
```

```python
@app.post("/users")
@permission_required("write")
async def create():
    return {"created": True}
```

```python
@app.delete("/users/<int:user_id>")
@permission_required("delete")
async def delete(user_id: int):
    return {"deleted": user_id}
```

---

# Role Decorator

Require a specific role.

```python
from flaxon.security import role_required

@app.get("/admin")
@role_required("admin")
async def admin():
    return {
        "message": "Welcome administrator."
    }
```

```python
@app.get("/moderator")
@role_required("moderator")
async def moderator():
    return {
        "message": "Moderator panel"
    }
```

---

# Combining Roles and Permissions

Sometimes both conditions should be met.

```python
from flaxon.security import authorize

@app.delete("/users/<int:user_id>")
@authorize(
    role="admin",
    permission="delete",
)
async def delete_user(user_id: int):
    return {
        "deleted": user_id
    }
```

---

# Authorization Checker

Permissions can also be checked manually.

```python
from flaxon.security import AuthorizationChecker

@app.get("/reports")
async def reports(request):

    checker = AuthorizationChecker(
        getattr(request, "user")
    )

    if not checker.has_permission("read"):
        raise HTTPException(
            403,
            "Permission denied.",
        )

    return await report_service.list()
```

---

# Requiring Multiple Permissions

Require one permission.

```python
checker.require_any_permission(
    "write",
    "delete",
)
```

Require every permission.

```python
checker.require_all_permissions(
    "read",
    "write",
)
```

---

# Resource Authorization

Applications often need ownership checks.

```python
@app.get("/users/<int:user_id>")
async def profile(request, user_id: int):

    user = getattr(
        request,
        "user",
    )

    if (
        user.id != user_id
        and "admin" not in user.roles
    ):
        raise HTTPException(
            403,
            "Access denied.",
        )

    return await user_service.find(user_id)
```

---

# Organization Authorization

Projects with teams or organizations can perform custom checks.

```python
@app.put("/organizations/<int:org_id>")
async def update_org(request, org_id: int):

    user = getattr(request, "user")

    if not organization_service.can_edit(
        user.id,
        org_id,
    ):
        raise HTTPException(
            403,
            "Not allowed.",
        )

    return {
        "updated": True
    }
```

---

# Custom Authorization Decorators

You can create your own decorators.

```python
from flaxon.security import authorization

@authorization
async def premium_required(user):

    return user.subscription == "premium"


@app.get("/premium")
@premium_required
async def premium():
    return {
        "premium": True
    }
```

---

# Complete Example

```python
from flaxon import (
    Flaxon,
    HTTPException,
)

from flaxon.security import (
    login_required,
    permission_required,
    role_required,
    authorize,
    register_permission,
    register_role,
)

app = Flaxon("authorization-demo")

register_permission(
    "read_users",
    "Read users",
)

register_permission(
    "write_users",
    "Write users",
)

register_permission(
    "delete_users",
    "Delete users",
)

register_permission(
    "manage_roles",
    "Manage roles",
)

register_role(
    "viewer",
    permissions=[
        "read_users",
    ],
)

register_role(
    "editor",
    permissions=[
        "read_users",
        "write_users",
    ],
)

register_role(
    "admin",
    permissions=[
        "read_users",
        "write_users",
        "delete_users",
        "manage_roles",
    ],
)

@app.get("/users")
@login_required
@permission_required("read_users")
async def users():
    return []

@app.post("/users")
@login_required
@permission_required("write_users")
async def create():
    return {
        "created": True
    }

@app.put("/users/<int:user_id>")
@login_required
@authorize(
    role="admin",
    permission="write_users",
)
async def update(user_id: int):
    return {
        "updated": user_id
    }

@app.delete("/users/<int:user_id>")
@login_required
@role_required("admin")
async def delete(user_id: int):
    return {
        "deleted": user_id
    }
```

---

# Best Practices

- Keep authentication and authorization separate.
- Prefer permissions over hard-coded role checks.
- Use role inheritance to reduce duplication.
- Apply the principle of least privilege.
- Protect every sensitive endpoint.
- Log authorization failures for auditing.
- Never trust client-provided roles or permissions.
- Validate authorization on every request.

---

# Next Steps

Continue with:

- Authentication
- Security
- Middleware
- GraphQL
- Admin Dashboard
- Databases
- Testing
- Deployment
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
