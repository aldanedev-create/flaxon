# Petal & Stem Admin Example

This editable example combines the Flaxon Admin dashboard, CMS, and a
WebSocket shop-floor chat room.

## Run

From the repository root:

```powershell
python -m pip install -e .[standard]
python -m flaxon run examples.flower_shop_admin.app:app --reload --port 8000
```

Open `http://127.0.0.1:8000/`.

- Admin: `/admin/`
- Custom Admin shop overview: `/admin/shop-overview`
- CMS SPA: `/admin/cms/`
- Chat room: `/chat?user=florist`

Development users are `owner / Owner123!` and `florist / Florist123!`.
Change them before deployment. After signing in, open the Admin profile and
enroll TOTP MFA. To require MFA on the first login, set a base32 secret in
`FLORAL_MFA_SECRET`; use `FLORAL_ADMIN_PASSWORD` and
`FLORAL_EDITOR_PASSWORD` for non-default passwords.

The Admin/CMS SQLite store is written to `data/admin.sqlite3`; uploads are
written to `data/uploads`. The flower catalog is deliberately an in-memory
model to make replacement with a project database straightforward. The chat
history is also in-memory; configure a persistent message repository and the
Redis broadcaster for multi-worker deployment.
