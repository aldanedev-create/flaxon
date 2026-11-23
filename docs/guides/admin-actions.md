# Admin actions

Flaxon Admin actions are reusable, class-based operations that an operator runs
from a model's change list: approve orders, export CSV, retry a job, and so on.
An `Action` bundles a label, prompt fields, a confirmation message, a scope,
authorization, an optional background mode, a result type and an audit entry.

Actions are **additive**: registration never changes the legacy
`register(Model, actions={...})` callables or the CMS `ContentType.register_action`
API. Every action runs behind CSRF protection and is capped by
`AdminConfig(action_bulk_limit=...)`.

## A minimal action

The example below is executed by `tests/docs/test_admin_actions_docs.py`.
`Order` is any registered model.

```python
from flaxon.admin.actions import Action, ActionResult, BULK

class MarkReviewed(Action):
    name = "mark_reviewed"
    label = "Mark reviewed"
    confirmation = "Mark the selected orders as reviewed?"
    scope = BULK

    async def handle(self, ids, params, context):
        return ActionResult.ok("Reviewed", data={"ids": list(ids)})

action = MarkReviewed()
dashboard.register_action(action, model=Order)
assert action.get_name() == "mark_reviewed"
assert action.scope == BULK
```

`register_action(action, model=...)` attaches the action to that model's action
selector and tracks it by name for background execution. Omit `model` to keep a
standalone action available only via the registry.

## Prompt fields and confirmation

Prompts ask the operator for input before an action runs. Values are validated
and coerced by `Prompt.clean()`; invalid input is rejected with HTTP 400 before
`handle()` runs. The `confirmation` text is shown in the browser's confirm
dialog.

```python
from flaxon.admin.actions import Prompt

prompts = [Prompt("mode", choices=("fast", "slow"), required=True)]
assert prompts[0].clean("fast") == "fast"
assert prompts[0].to_dict()["choices"] == ["fast", "slow"]
```

## The two shipped examples

`ApproveOrders` marks selected records as approved and reports failures per
record. `ExportCsv` downloads selected records as a spreadsheet-injection-safe
CSV (cells beginning with `=`, `+`, `-` or `@` are prefixed with `'`).

```python
from flaxon.admin.actions import ApproveOrders, ExportCsv

approve = ApproveOrders()
export = ExportCsv()
assert approve.name == "approve_orders"
assert export.name == "export_csv"
assert approve.to_schema()["confirmation"]
```

Both examples work end to end in `tests/integration/test_admin_actions_api.py`,
and the browser flow is captured from a real running app in
`tests/browser/test_admin_actions_browser.py`:

![Admin actions in a real browser](../assets/readme/admin-actions.png)

## Authorization and safety

Override `can_run()` for object-aware authorization. Returning `False` yields
HTTP 403 with no side effects. Legacy permission checks still apply, so access
is denied if either layer rejects the user.

```python
class ManagersOnly(MarkReviewed):
    name = "managers_only"
    permission = "order.managers_only_order"

    async def can_run(self, user, dashboard, **kwargs):
        return "manager" in getattr(user, "roles", [])

guarded = ManagersOnly()
assert guarded.permission == "order.managers_only_order"
```

Unauthorized users get 403 and no side effects; failures are reported per
record; bulk size is capped by `AdminConfig(action_bulk_limit=...)`; and each
run writes a full entry to the immutable audit log.

## Result types and background execution

`handle()` returns one of four result types:

| Result | Factory | Effect |
| --- | --- | --- |
| message | `ActionResult.ok("Done")` | Redirect back to the change list |
| redirect | `ActionResult.redirect(url)` | Redirect to a custom URL |
| download | `ActionResult.download(name, content)` | Stream a file attachment |
| danger | `ActionResult.danger("Failed", errors=[...])` | Report a failed result |

```python
from flaxon.admin.actions import ActionResult

assert ActionResult.ok("Done").kind == "message"
assert ActionResult.redirect("/admin/order").kind == "redirect"
assert ActionResult.download("x.csv", "a,b\n").kind == "download"
assert ActionResult.danger("Failed").kind == "danger"
```

Set `background = True` to enqueue the action onto the existing durable job
system instead of running it inline. The queued payload carries the action name,
model, ids and cleaned prompt values, and `dashboard.run_action_job(payload)`
executes it without an HTTP request.
