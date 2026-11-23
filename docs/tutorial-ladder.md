# Tutorial ladder: build a Flask-free Flaxon app in five steps

This ladder teaches the framework in small, verified steps. Each rung has a
**goal**, **code**, a **run** command, a **check** you can execute, and a
**recap**. Every code block here is executed by `tests/docs/test_ai_docs.py`.

## Rung 1 — A JSON endpoint

**Goal.** Serve a JSON response and test it without starting a server.

**Code.**

```python
from flaxon import Flaxon

app = Flaxon("ladder")


@app.get("/ping")
async def ping():
    return {"pong": True}
```

**Run.** `uvicorn app:app` (install `flaxon[standard]`).

**Check.**

```python
from flaxon.testing import TestClient

assert TestClient(app).get("/ping").json() == {"pong": True}
```

**Recap.** A `Flaxon` app is an ASGI app; decorators register routes; typed path
parameters use `<int:id>`.

## Rung 2 — Validate input

**Goal.** Reject invalid input with the documented error shape.

**Code.**

```python
from flaxon.validation import IntField

age = IntField(minimum=0, maximum=120)
age.bind("age")
```

**Check.**

```python
assert age.deserialize("42") == 42
assert age.validate(42) is None
```

**Recap.** Validation errors are HTTP 422 with `error.code == "FX-VAL-001"`
and an `error.fields` map; fields validate with the same rules as the API.

## Rung 3 — Persist a model

**Goal.** Define a model and read it back.

**Code.**

```python
from flaxon.db import Model, fields


class LadderNote(Model):
    text = fields.CharField(max_length=80)

    class Meta:
        app = "ladder"
        table = "ladder_note"
```

**Recap.** `flaxon.db` re-exports Tortoise `Model` and `fields`; connection
setup uses `Tortoise.init`. See [the DB recipe](ai/recipes/database.md).

## Rung 4 — Add admin

**Goal.** Give the model a full admin with one resource class.

**Code.**

```python
from typing import ClassVar

from flaxon.admin.resources import Field, Resource, Text


class LadderNoteResource(Resource):
    model = LadderNote
    fields: ClassVar[list[Field]] = [Text("text", required=True).searchable()]
```

**Recap.** A `Resource` subclass is under 10 lines; legacy `register(...)`
options still work. See [the admin recipe](ai/recipes/admin-resource.md).

## Rung 5 — Compile a Teloce component

**Goal.** Ship an interactive control without Node.

**Code.**

```python
from flaxon.admin import Component

component = Component("badge", "<template><span>{{ text }}</span></template>")
assert component.name == "badge"
```

**Recap.** Flaxon compiles `.vel` components with the bundled Teloce toolchain;
cards and pages render server-side first, then enhance in the browser. See
[the Teloce field recipe](ai/recipes/teloce-field.md).
