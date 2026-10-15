# Northstar Academy — Teloce interface on the Flaxon ORM

The same school portal as [`../school_portal_orm`](../school_portal_orm), but the
public site is a **Teloce single-page interface** instead of server-rendered
Jinax templates. The backend is unchanged: `flaxon.db` (Tortoise) models, the
staff **Admin**, and the **CMS**. The SPA talks to a small JSON API that reads the
same tables and content the Admin edits.

This demonstrates the three layers working together in one Flaxon app:

| Layer | Where | Role |
| --- | --- | --- |
| Data | `models.py` | `flaxon.db` models: `Student`, `Course`, `Staff`, `Enrollment` (foreign key) |
| Admin + CMS | `admin.py`, `app.py` | Staff edit the catalogue; `ADMIN_STORE_BACKEND = "orm"` |
| API | `modules/portal.py` | JSON endpoints (`/api/...`) backed by the ORM and CMS |
| Interface | `ui/` | Teloce `.html` components compiled by `app.use_teloce()` |

## Run it

```bash
cd examples/school_portal_teloce
python management.py migrate          # creates the ORM tables + admin tables
python management.py setup-admin       # create the first staff account
python seed.py                         # load the demo catalogue and CMS content
python management.py runserver         # http://127.0.0.1:8000
```

Open the site at http://127.0.0.1:8000. Sign in to the staff Admin at
`/admin/` with the credentials printed by `setup-admin`.

## Behind a reverse proxy (GitHub Codespaces, tunnels)

The Teloce live reload / development diagnostics compare the browser's `Origin`
(`https://…`) with what the server sees. When Flaxon runs behind the Codespaces
proxy, the proxy connects over plain `http` and forwards the real scheme/host in
`X-Forwarded-Proto` / `X-Forwarded-Host`, but the dev server **ignores** those
headers unless the proxy IP is trusted. Two things then look mismatched:

- `teloce.py` turns live reload off — *"Development diagnostics require the same
  origin. The browser sent http://localhost:8000 but the server sees
  https://localhost:8000."*
- `TrustedHostsMiddleware` rejects the Codespaces host (it is not in
  `ALLOWED_HOSTS`).

The Codespaces proxy already sends the forwarded headers — you only need to make
Flaxon trust them and allow the public host. **Important:** Flaxon's
`TrustedHostsMiddleware` does *not* treat `*` as a wildcard, so `ALLOWED_HOSTS`
must contain the *exact* forwarded host (copy it from your browser's address bar
when you open the forwarded port — typically `${CODESPACE_NAME}-8000.app.github.dev`).

```bash
# 1) Env vars with the bundled runserver (uvicorn reads FORWARDED_ALLOW_IPS):
FLAXON_ALLOWED_HOSTS="${CODESPACE_NAME}-8000.app.github.dev" \
FORWARDED_ALLOW_IPS='*' \
python management.py runserver

# 2) Framework `run` command, which has a first-class flag:
FLAXON_ALLOWED_HOSTS="${CODESPACE_NAME}-8000.app.github.dev" \
flaxon run app:app --forwarded-allow-ips '*' --reload --port 8000

# 3) Plain runserver, letting the app own the proxy trust (see app.py):
FLAXON_ALLOWED_HOSTS="${CODESPACE_NAME}-8000.app.github.dev" \
FLAXON_TRUST_PROXY=1 \
python management.py runserver
```

`FORWARDED_ALLOW_IPS='*'` (or `FLAXON_TRUST_PROXY=1`) makes Flaxon rewrite the
seen scheme/host from `X-Forwarded-*` so the browser's `https` origin matches;
use `'*'` for the proxy trust **only** in development. The `FLAXON_ALLOWED_HOSTS`
value must stay the concrete public host — never `*` (it would be rejected by
the host check, and Flaxon blocks `*` in production anyway).

## What to look at

- `ui/app.html` — the shell, navigation, and router outlet.
- `ui/pages/Home.html` — fetches `/api/overview` and `/api/news` on mount.
- `ui/pages/Students.html`, `Courses.html`, `News.html`, `Events.html` — each page
  fetches its JSON endpoint and renders Teloce components.
- `modules/portal.py` — the API. Note `Enrollment` uses a Tortoise foreign key and
  `POST /api/enrollments` writes through the ORM directly (no Admin involved), so
  a new enrollment created in the browser appears in Admin and vice versa.
- `app.py` — `app.use_teloce()` is configured **before** the management guard so
  build/typecheck still work; the SPA catch-all coexists with `/admin/*` because
  Admin registers exact static routes that win over the dynamic fallback.

## Differences from `school_portal_orm`

- The public pages are a client-side Teloce SPA (`ui/`) rather than Jinax
  templates, served by `request.compile("app.html", context)`.
- Data reaches the browser through a JSON API (`modules/portal.py`) instead of
  server-side template rendering.
- Adds an `Enrollment` model with two foreign keys to show related data and a
  non-Admin write path.

Both examples share the identical Admin/CMS/ORM backend, so the same staff login,
audit log, and content workflow apply.
