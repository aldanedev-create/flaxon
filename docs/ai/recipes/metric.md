# Recipe: a dashboard metric

Metrics calculate in Python/SQL and render as inline SVG. Subclass `Metric`
(or use a built-in like `Value`) and register it on the dashboard.

```python
from flaxon.admin.metrics import Value

total_books = Value("Total books", aggregate="count", description="All books")
assert total_books.title == "Total books"
assert total_books.kind == "value"
```

Register a metric so it appears on the dashboard with access control:

```python
from flaxon import Flaxon
from flaxon.admin import AdminDashboard

app = Flaxon("metric-recipe")
dashboard = AdminDashboard(
    app,
    store=None,
    users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
    upload_dir="/tmp/flaxon-metric-recipe-uploads",
)
dashboard.register_metric(total_books)
assert any(metric.title == "Total books" for metric in dashboard.metrics)
```
