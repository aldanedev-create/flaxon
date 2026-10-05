# Northstar Academy school portal

This is a small, runnable school website that demonstrates how Flaxon modules
keep a larger application organized while Flaxon Admin and CMS provide the
back-office workflow.

```text
examples/school_portal/
|-- app.py                         # app factory and composition root
|-- modules/
|   |-- repository.py              # replace with your database repository
|   |-- website.py                 # public school pages and calendar
|   |-- academics.py               # academic pages and JSON API
|   `-- community.py               # CMS-backed news page and API
|-- templates/                     # Jinax public and custom Admin pages
`-- static/                        # public site styling and campus image
```

## Run it

From the repository root:

```bash
python -m pip install -e ".[standard]"
flaxon run examples.school_portal.app:app --reload --port 8000
```

Open:

| URL | Purpose |
|---|---|
| `http://127.0.0.1:8000/` | Public school homepage |
| `http://127.0.0.1:8000/about` | Mission, commitments, and staff |
| `http://127.0.0.1:8000/academics` | Academic approach and course highlights |
| `http://127.0.0.1:8000/academics/courses` | Module-owned course directory |
| `http://127.0.0.1:8000/students` | Student life and community |
| `http://127.0.0.1:8000/admissions` | Admissions process |
| `http://127.0.0.1:8000/calendar` | CMS-backed school events |
| `http://127.0.0.1:8000/news` | CMS-backed published news |
| `http://127.0.0.1:8000/contact` | Main office and visit information |
| `http://127.0.0.1:8000/admin/login` | Admin login |
| `http://127.0.0.1:8000/admin/` | Admin dashboard |
| `http://127.0.0.1:8000/admin/cms/` | CMS workspace |
| `http://127.0.0.1:8000/admin/school-overview` | Custom Admin page |

Development login: `admin` / `School123!`. Set
`FLAXON_SCHOOL_ADMIN_PASSWORD` before deployment.

## What to test in Admin

- Search, filter, sort, paginate, create, edit, and delete Students, Courses,
  and Staff.
- Open the custom School overview page from the Admin navigation.
- Create a News item in CMS, set it to `published`, and refresh `/news`.
- Create or edit an Event in CMS, set it to `published`, and refresh `/calendar`.
- Try `/api/courses` and `/api/news` as the public read APIs.
- Change a record, restart the app, and confirm the JSON repository retained it.

## Copy the module pattern

Create one module for each business capability:

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

Compose modules once in the application factory:

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule

app = Flaxon("school")
app.container.register_instance("school", repository)
app.mount_module(academics, prefix="/academics")
```

The module does not start a second server and does not know its final prefix.
The application chooses the mount path, which makes the feature reusable for
`/academics`, `/api/v1/academics`, or an Admin extension. See the complete
[Modules guide](../../docs/guides/Modules.md) for hooks, nested modules,
templates, static files, tests, and CLI commands.

## Production changes

The JSON repository is intentionally small for a copy-paste demo. Replace it
with a database-backed repository, use a persistent Admin store, configure
Redis for multiple workers, move media to object storage, and load the Admin
password from a secret manager.
