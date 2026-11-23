# Recipe: a class-based admin action

Actions declare prompts, authorisation and a handler that returns a typed
`ActionResult`. Unauthorised runs never call `handle`.

```python
from flaxon.admin.actions import Action, ActionContext, ActionResult


class ApproveBooks(Action):
    name = "approve_books"
    label = "Approve selected books"
    description = "Mark selected books as approved."
    confirmation = "Approve the selected books?"
    permission = "book.manager"

    async def handle(self, context: ActionContext) -> ActionResult:
        return ActionResult.ok("Approved")


action = ApproveBooks()
assert action.get_name() == "approve_books"
assert action.get_label() == "Approve selected books"
```

`ActionResult` types are transport-independent:

```python
assert ActionResult.ok("done").kind == "message"
assert ActionResult.redirect("/admin/book").kind == "redirect"
assert ActionResult.download("books.csv", "id\n1\n").kind == "download"
```
