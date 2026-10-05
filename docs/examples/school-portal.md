# School portal: Admin plus Flaxon modules

The runnable [`examples/school_portal/`](../../examples/school_portal/) project
is a small Northstar Academy website. It demonstrates the application shape
to copy when building a larger product:

```text
school_portal/
|-- app.py
|-- modules/
|   |-- repository.py
|   |-- website.py
|   |-- academics.py
|   `-- community.py
|-- templates/
`-- static/school.css
```

## Run the example

From the Flaxon repository root:

```bash
python -m pip install -e ".[standard]"
flaxon run examples.school_portal.app:app --reload --port 8000
```

Open the public site at <http://127.0.0.1:8000/>. The Admin login is at
<http://127.0.0.1:8000/admin/login> with the development credentials
`admin` / `School123!`. Set `FLAXON_SCHOOL_ADMIN_PASSWORD` before using the
example outside local development.

The example includes:

- Admin-managed Students, Courses, and Staff models with search, filters,
  sorting, pagination, CRUD, and persistent JSON demo records.
- CMS-managed News and Events content types. Publish an item in
  `/admin/cms/` and it appears in the public bulletin or school calendar.
- A custom Admin page at `/admin/school-overview`.
- Public module-owned pages at `/`, `/about`, `/academics`,
  `/academics/courses`, `/students`, `/admissions`, `/contact`, `/calendar`,
  and `/news`, plus JSON APIs at `/api/courses` and `/api/news`.

The public site includes a responsive institutional navigation, a campus hero
image, a featured news layout, an events calendar, admissions calls to action,
and a staff directory. The visual pages are ordinary Jinax templates, so a
developer can replace the content or connect the same routes to a database
without changing the Admin/CMS setup.

## Copy the module pattern

Each feature declares only the dependencies it needs and owns its routes:

```python
from flaxon.modules import FlaxonModule

academics = FlaxonModule("academics")
academics.requires("school")


@academics.get("/courses")
async def courses(request, school):
    return await request.render(
        "courses.html",
        {"title": "Courses", "courses": await school.list("courses")},
    )
```

The application factory provides services and chooses URL prefixes:

```python
from flaxon import Flaxon

app = Flaxon("school")
app.container.register_instance("school", repository)
app.mount_module(academics, prefix="/academics")
```

The module is reusable because it does not start a server and does not bake a
prefix into its routes. Mount the same feature under `/academics`, `/api/v1`,
or an authenticated Admin extension when the application needs it. Use the
[Modules guide](../guides/Modules.md) for hooks, nested modules, templates,
static files, CLI commands, and module tests.

The example's JSON repository is intentionally easy to replace. In production,
use a database repository, persistent Admin storage, Redis for shared workers,
secret-managed credentials, and object storage for media.
