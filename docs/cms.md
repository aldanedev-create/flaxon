# Flaxon CMS

For generated projects, use the shared `settings.py`, `Flaxon.from_settings()`,
explicit mounts in `app.py`, and `management.py` workflow. See [ORM and project management](guides/orm.md)
for Python migrations, model registration, permission hooks, relationship editing,
and Admin/CMS metadata storage. Backend-only and legacy adapter examples remain supported.

This page is kept as a stable entry point for existing links. The current CMS
implementation, production setup, API contract, persistence, security model,
SPA behavior, editorial workflows, and customization examples are maintained
in the [Admin and CMS Production Guide](guides/admin-cms.md).

For a runnable editable application, see
[`docs/examples/cms/full_admin_cms/app.py`](examples/cms/full_admin_cms/app.py).

The CMS is mounted with:

```python
from flaxon.admin.cms import CMS

cms = CMS(app, url_prefix="/admin/cms", auth=admin.auth)
```

Use `CMSField` and `ContentType` to define schemas. The bundled SPA is a
replaceable client of the authenticated JSON API; custom frontends must send
the `X-CSRF-Token` header for every mutation.
