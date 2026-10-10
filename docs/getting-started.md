# Getting started with Flaxon

Build a complete application with Python APIs, Teloce HTML components, TypeScript, scoped styles, and a protected admin in one project.

## Create your first application

Use Python 3.11 or newer. Install Flaxon in a virtual environment, then generate the starter:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install "flaxon[standard]"
flaxon new my-project
cd my-project
python -m pip install -e .
python management.py check
python management.py makemigrations
python management.py migrate
python management.py setup-admin
python management.py runserver
```

Open **http://127.0.0.1:8000/**. The welcome page's **Try your Python API** button calls `/api/welcome/status` through a TypeScript helper. Open `/admin/login` to sign in with the account you created.

There is no preset administrator or password. `setup-admin` (also `createsuperuser`) accepts your chosen nonempty password, up to 128 characters. With `DEBUG=True`, no strength warning is shown. With `DEBUG=False`, a weak password produces a recommendation for a long, unique production password but is still accepted. Confirmation must match. Other Admin account creation, password changes, and resets retain their existing validation policy. Password entry is hidden; passwords are hashed before storage. Create accounts before starting the server, or restart it after adding an account from the command line.

`flaxon new my-project --template basic` keeps the smaller Python API starter available. The default `fullstack` template includes the interface, module, database, and admin.

## Choose your interface

Flaxon supports complete websites with **Jinax** (server-rendered HTML templates) and interactive applications with **Teloce** (compiled HTML components and TypeScript). The starter demonstrates both: `/` uses Teloce and `/server-page` uses Jinax. You can choose either for your whole application or combine them.

For a Jinax-only application, keep `app.use_templates(...)`, remove `app.use_teloce(...)`, and change the root route to return `app.jinax.render_response("welcome.html", {"project_name": PROJECT_NAME})`. Your Python modules, API routes, database, and admin remain available.

## Understand the generated project

| File or directory | Purpose |
| --- | --- |
| `app.py` | Compose the application, mount the module, configure Teloce, and serve `/`. |
| `templates/welcome.html` | Complete Jinax HTML page at `/server-page`. |
| `flaxon_cli.py` | Register custom commands owned by your feature modules. |
| `settings.py` | Shared database URL, security, paths, and enabled features. |
| `modules/welcome/module.py` | Your first module-owned Python API. |
| `modules/welcome/ui/Welcome.html` | Welcome component with `lang="ts"` and scoped CSS. |
| `modules/welcome/ui/api.ts` | Typed browser helper for the module API. |
| `ui/app.html` | Root component importing the welcome interface. |
| `public/` | Global CSS and favicon served at `/assets`. |
| `management.py` | Project-local migrations and administrator creation. |
| `models.py` / `admin.py` | ORM schema and explicit Admin registration. |
| `migrations/` | Generated Python migrations from model changes. |
| `data/` | Local database and uploads; excluded from Git. |

Teloce compiles the browser code; Flaxon handles requests, Python modules, persistence, and administration. The welcome example does not need a separate Node development server.

## Run and extend module-owned commands

From the generated project directory, run:

```bash
flaxon welcome
flaxon welcome-status
```

These commands live in `modules/welcome/module.py`, using `@welcome.cli_command(...)`. The first is synchronous; the second awaits the module's async status helper. `flaxon_cli.py` exposes them with `welcome.install_cli_commands(globals())`. They work without starting the web server or connecting to a database. Add commands to another feature module and install them in `flaxon_cli.py`; use unique names that do not conflict with built-in commands. See the [module guide](guides/Modules.md) and [CLI guide](lessons/Cli.md).

The welcome page links to the [documentation website](https://flaxon-website.vercel.app/docs.html) and uses its hosted logo. The logo and external documentation require internet access; local routes and commands work offline.

## Change the application

1. Edit `modules/welcome/module.py` to add a Python endpoint.
2. Update `api.ts` to call that endpoint and describe its response with a TypeScript interface.
3. Update `Welcome.html` to show the result. Its scoped styles belong to the component.
4. Add a module for each feature and mount it in `app.py`. Keep its UI beside its Python routes.
5. Edit models, run `python management.py makemigrations`, review the generated Python migration, then run `python management.py migrate`.

Check migration status with `python management.py migrate --status`. `python management.py createsuperuser` is an alias for `setup-admin`; existing usernames are never overwritten. Run `python management.py --help` for command help.

## Learn the rest of Flaxon

Follow the [ten full-stack lessons](fullstack/index.md) in order, from your first application through TypeScript, navigation, modules, persistence, live updates, and deployment.

| Next step | Documentation |
| --- | --- |
| Installation and alternatives | [Installation](installation.md), [quick start](quickstart.md) |
| Server foundations | [Routing](guides/routing.md), [requests](guides/requests.md), [responses](guides/responses.md), [validation](guides/validation.md) |
| UI and browser code | [Teloce SPA guide](guides/Teloce-Spa.md), [Teloce API](api/teloce.md), [components lesson](fullstack/02-components.md), [TypeScript lesson](fullstack/04-typescript.md) |
| Application structure | [Modules](guides/Modules.md), [module lesson](fullstack/07-modules.md), [configuration](configuration.md) |
| Data and users | [Databases](guides/databases.md), [authentication](guides/authentication.md), [authorization](guides/authorization.md) |
| Admin and content | [Admin guide](admin-guide.md), [admin/CMS](guides/admin-cms.md), [production admin](guides/admin-production.md) |
| Other server capabilities | [Tasks](guides/tasks.md), [WebSockets](guides/websockets.md), [mail](mail.md), [GraphQL](graphql.md), [plugins](guides/plugins.md) |
| Ship and maintain | [Testing](guides/testing.md), [security](security.md), [deployment](deployment.md), [maintenance](maintenance.md) |
| Complete reference and examples | [All documentation](index.md#complete-documentation-directory) |

Before deployment, set `FLAXON_DEBUG=0`, use HTTPS, review permissions, back up `data/`, and follow the deployment and production-admin guides. The starter uses local SQLite and local uploads for a single application instance. Deploy the project sources or an editable installation; packaging your own application as a wheel requires including its UI and public files.

See [ORM and settings](guides/orm.md) for the complete management workflow and legacy migration transition.
