# Flaxon cookbook

Four end-to-end patterns, each with code that is executed by
`tests/docs/test_ai_docs.py`. For a step-by-step introduction start with the
[tutorial ladder](tutorial-ladder.md); for canonical minimal examples see
[`docs/ai/recipes/`](ai/recipes/api.md).

## Approve an action

Declare a class-based action with authorisation and a typed result.

```python
from flaxon.admin.actions import Action, ActionContext, ActionResult


class ApproveOrders(Action):
    name = "approve_orders"
    label = "Approve orders"
    permission = "order.manager"
    confirmation = "Approve the selected orders?"

    async def handle(self, context: ActionContext) -> ActionResult:
        return ActionResult.ok("Approved")


assert ApproveOrders().get_name() == "approve_orders"
```

Unauthorised users get 403 with no side effects; failures are reported per
record. See [the action guide](guides/admin-actions.md).

## Import CSV safely

Map columns, enforce caps and neutralise spreadsheet formulas.

```python
from flaxon.admin.importing import csv_safe, enforce_limits, map_columns

rows, errors = map_columns([{"email": "a@example.com"}], {"email": "username"})
assert rows == [{"username": "a@example.com"}]
assert errors == []
assert csv_safe("=SUM(A1)") == "'=SUM(A1)"
enforce_limits(payload_bytes=10, row_count=1, max_bytes=100, max_rows=5)
```

Exports pass every value through `csv_safe`; imports support a dry run and
row-level errors. See [the filters and safety guide](guides/admin-filters-and-safety.md).

## Render a revenue chart

Metrics compute in SQL and render as inline SVG, offline and dark-mode aware.

```python
from flaxon.admin.metrics import Trend

revenue = Trend("Revenue", range="30d", description="Last 30 days")
assert revenue.title == "Revenue"
assert revenue.kind == "trend"
```

See [the metrics guide](guides/admin-metrics.md).

## Add a custom field

A Teloce field is a validated `Field` with a component and an HTML fallback.

```python
from flaxon.admin import Component, TeloceField

sentiment = TeloceField(
    "sentiment",
    Component("sentiment", "<template><select :name='name'></select></template>"),
    fallback="select",
    fallback_choices=[("happy", "Happy"), ("sad", "Sad")],
)
assert sentiment.schema_entry()["kind"] == "teloce"
assert sentiment.clean("happy") == "happy"
```

See [the extensions guide](guides/admin-extensions.md) to package the field as
a `flaxon-admin-*` plugin.
