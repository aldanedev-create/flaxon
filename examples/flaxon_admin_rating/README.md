# flaxon-admin-rating

A complete example [Flaxon](../../README.md) admin extension. It adds a 1–5 star
field, a dashboard card, a page and a tool to the admin — all UI written as
[Teloce](../../docs/api/teloce.md) `.vel` components, compiled in Python. No Node.js,
npm, bundler or CDN is involved.

## Install and run

```bash
cd examples/flaxon_admin_rating
python -m pip install -e .
python -m flaxon run app:app --port 8000
```

Open <http://127.0.0.1:8000/admin/login> and sign in with `admin` / `Admin123!`.
`app.py` defines a `Product` model with a `rating` column and a
`ProductResource` that uses `RatingField`.

## What it contributes

| Contribution | Where it appears |
| --- | --- |
| `RatingField` | Product create/edit forms, with a five-star control and an HTML `select` fallback |
| `RatingCard` | Dashboard card with the average rating and 1–5 distribution |
| `RatingPage` | `/admin/ratings`, listing every model that uses `RatingField` |
| `Tool` | "Rating insights" shortcut on the dashboard |
| `admin.view_ratings` | Permission required by the page |

The card is added per model through `model_registered`, so registering another
resource with `RatingField("rating")` adds its own card.

## Use it in your app

```python
from flaxon.admin.resources import Resource, Text
from flaxon_admin_rating import RatingField


class ProductResource(Resource):
    model = Product
    fields = [Text("name").searchable(), RatingField("rating", required=True)]
```

The package is discovered through the `flaxon.admin` entry point declared in
`pyproject.toml`; nothing needs to be imported in the application module. Pass
`AdminConfig(disabled_extensions=("rating",))` to keep it installed but off.

## Files

```
flaxon_admin_rating/
├── __init__.py          # RatingField, RatingCard, RatingPage, RatingExtension
└── ui/
    ├── rating.vel           # interactive star control (form field)
    ├── rating-summary.vel   # dashboard card
    └── ratings.vel          # insights page
app.py                   # runnable demo app
```

## Notes

- Values are validated in Python (`IntField(minimum=1, maximum=5)`), not only in
  the browser.
- The page requires `admin.view_ratings`; the admin superuser has it implicitly.
- Aggregation uses one grouped SQL query, not a Python row loop.
- Teloce's static renderer interpolates text and repeats `v-for` blocks; dynamic
  attribute bindings are applied when the component mounts. The field therefore
  ships a real `<select>` fallback for the no-JavaScript path.
