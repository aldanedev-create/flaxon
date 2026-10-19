"""The one table this example needs: a saved system design.

Run `python management.py makemigrations` after editing, then `migrate`.

`graph` is a JSON blob holding `{"nodes": [...], "edges": [...]}`. It is
deliberately schemaless: the browser owns the shape of a design (see
`static/js/island.js`) and Flaxon only validates it before storing it.
"""
from flaxon.db import Model, fields


class Design(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120)
    scenario = fields.CharField(max_length=40, default="calm-day")
    seed = fields.IntField(default=7)
    graph = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "island_designs"

    def __str__(self):
        return self.name
