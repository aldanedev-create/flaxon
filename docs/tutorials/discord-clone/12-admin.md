# Lesson 12: Flaxon Admin for moderation

Your `models.py` is already Admin-ready — Flaxon derives list views, search,
filters, and edit forms from the field definitions. `admin.py` just registers
the models you want staff to moderate:

```python
def register(admin):
    admin.register(User, list_display=[...], search_fields=["username", "email"], ...)
    admin.register(Server, ...)
    admin.register(Message, search_fields=["content"], list_filter=["type"], ...)
    # ChannelAccess is intentionally NOT registered: pure authorization, API-only.
```

Admin is mounted at `/admin/` and uses its own signed session. Create the first
staff account with the management command (it writes to the admin store, which is
ORM-backed in this project):

```bash
python management.py setup-admin
```

Admin runs with `strict_permissions=True`, so a new admin gets an explicit
`admin.superuser` grant rather than implicit access. The dashboard is protected:
an unauthenticated request to `/admin/` is bounced to the login page — the
permission separation between the public app and the staff console.

**Checkpoint:** `GET /admin/login` returns the login page (`200`); `GET /admin/`
without a session returns `302` to login. Log in and confirm the User, Server,
and Message models are listed with search and filters. The tests in
`tests/test_admin_cms.py` pin both behaviours.
