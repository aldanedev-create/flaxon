# Recipe: a Tortoise model and query

Flaxon's `flaxon.db` re-exports `Model` and `fields`; connection setup uses
Tortoise directly. Define a model, initialise an in-memory database, create a
row and query it.

```python
import asyncio
import sys
from types import ModuleType

from tortoise import Tortoise
from flaxon.db import Model, fields

recipe_models = ModuleType("recipe_models")
sys.modules["recipe_models"] = recipe_models


class Note(Model):
    title = fields.CharField(max_length=120)

    class Meta:
        app = "recipe_models"
        table = "recipe_note"


Note.__module__ = "recipe_models"
recipe_models.Note = Note
```

```python
async def main():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"recipe_models": ["recipe_models"]})
    await Tortoise.generate_schemas()
    note = await Note.create(title="Hello")
    assert (await Note.get(id=note.id)).title == "Hello"
    await Tortoise.close_connections()


asyncio.run(main())
```
