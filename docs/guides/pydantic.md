# Pydantic Integration

Pydantic support is optional. Flaxon keeps its core validation system
independent, while the integration lets endpoints accept Pydantic `BaseModel`
parameters and return model instances.

## Install

```bash
python -m pip install "flaxon[pydantic]" email-validator
```

## Validate request bodies

```python
from pydantic import BaseModel, EmailStr

from flaxon import Flaxon

app = Flaxon("accounts")


class CreateUser(BaseModel):
    name: str
    email: EmailStr
    age: int


@app.post("/users")
async def create_user(user: CreateUser) -> CreateUser:
    return user
```

Invalid JSON returns `400`. Valid JSON that fails the model returns `422` with
field-level errors under `error.fields`.

## Response models

Returning a Pydantic model is supported directly. Flaxon serializes it with
`model_dump()` while preserving normal JSON response behavior.

```python
@app.get("/users/<user_id>")
async def get_user(user_id: str) -> CreateUser:
    return CreateUser(name="Ava", email="ava@example.com", age=28)
```

Flaxon's native `Schema` classes remain supported and are a good choice when
you do not want an additional dependency.

## Use Pydantic with modules

For a larger application, keep the model and endpoint inside the feature that
owns them. Mount that feature once from the application factory:

```python
# app/modules/accounts/module.py
from typing import Any

from pydantic import BaseModel, EmailStr

from flaxon.modules import FlaxonModule

accounts = FlaxonModule("accounts")


class CreateAccount(BaseModel):
    name: str
    email: EmailStr


@accounts.post("/")
async def create_account(account: CreateAccount) -> CreateAccount:
    return account


def install_accounts(app: Any) -> None:
    app.mount_module(accounts, prefix="/api/accounts")
```

```python
# app/main.py
from flaxon import Flaxon
from app.modules.accounts.module import install_accounts


def create_app() -> Flaxon:
    app = Flaxon("accounts", debug=False)
    install_accounts(app)
    return app


app = create_app()
```

The endpoint is `POST /api/accounts/`. The model is close to the route, while
the factory owns only application composition. Put database writes in a
service or repository rather than in the Pydantic model or route handler.

For a complete runnable version, see
`examples/pydantic_api/`. Start it with:

```bash
flaxon run examples.pydantic_api.app:app --reload
```
