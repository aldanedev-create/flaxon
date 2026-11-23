# Recipe: a declarative admin resource

Turn a model into a full admin in a few lines with a `Resource` subclass and
`Field` declarations, then register it on the dashboard.

```python
from typing import ClassVar

from flaxon.db import Model, fields
from flaxon.admin.resources import Field, Resource, Text


class Book(Model):
    title = fields.CharField(max_length=120)

    class Meta:
        app = "recipes"
        table = "recipe_book"


class BookResource(Resource):
    model = Book
    fields: ClassVar[list[Field]] = [
        Text("title", required=True).searchable().sortable(),
    ]
```

The legacy registration API stays valid; the new API is additive. Wire the
resource into a dashboard with an explicit include:

```python
from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard

app = Flaxon("admin-recipe")
dashboard = AdminDashboard(
    app,
    config=AdminConfig(),
    store=None,
    users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
    upload_dir="/tmp/flaxon-admin-recipe-uploads",
)
dashboard.register(BookResource)
assert any(model.get_name() == "book" for model in dashboard.registry.get_all())
```
