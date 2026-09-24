# Admin API Reference

## Admin Dashboard

::: flaxon.admin.AdminDashboard
    options:
        members:
            - __init__
            - register
            - add_view
            - mount_module
            - register_widget
            - register_permission
            - unregister
            - index
            - list_view
            - add_view
            - detail_view
            - edit_view
            - delete_view
            - get_urls

---

## Admin Configuration

::: flaxon.admin.AdminConfig
    options:
        members:
            - __init__
            - to_dict

---

## Registry

::: flaxon.admin.Registry
    options:
        members:
            - register
            - unregister
            - get
            - get_by_model
            - get_all
            - clear

---

## Admin Model

::: flaxon.admin.registry.AdminModel
    options:
        members:
            - __init__
            - get_name
            - get_verbose_name
            - get_verbose_name_plural
            - add_action
            - get_actions

---

# Admin Views

## Base View

::: flaxon.admin.views.AdminView
    options:
        members:
            - __init__
            - render

---

## Change List View

::: flaxon.admin.views.ChangeListView
    options:
        members:
            - render

---

## Detail View

::: flaxon.admin.views.DetailView
    options:
        members:
            - render

---

## Create View

::: flaxon.admin.views.CreateView
    options:
        members:
            - render

---

## Update View

::: flaxon.admin.views.UpdateView
    options:
        members:
            - render

---

## Delete View

::: flaxon.admin.views.DeleteView
    options:
        members:
            - render

---

# Decorators

## admin_model

::: flaxon.admin.decorators.admin_model
    options:
        show_source: false

---

## admin_action

::: flaxon.admin.decorators.admin_action
    options:
        show_source: false

---

## admin_display

::: flaxon.admin.decorators.admin_display
    options:
        show_source: false

---

# Exceptions

## AdminError

::: flaxon.admin.exceptions.AdminError

---

## ModelNotFoundError

::: flaxon.admin.exceptions.ModelNotFoundError

---

## PermissionDeniedError

::: flaxon.admin.exceptions.PermissionDeniedError

---

## ValidationError

::: flaxon.admin.exceptions.ValidationError

## Production Services

These services are available for durable Admin integrations:

```python
from flaxon.admin import (
    DurableJobStore, DurableJobWorker, ImmutableAuditLog,
    NotificationService, ResumableUploadStore, WebAuthnService,
)
```

| Service | Purpose |
|---|---|
| `DurableJobStore` | Persist queued, running, completed, and failed jobs with retry metadata. |
| `DurableJobWorker` | Register named handlers and process due jobs. |
| `ImmutableAuditLog` | Append hash-chained records and verify tamper evidence. |
| `NotificationService` | Store preferences and per-user channel delivery records. |
| `ResumableUploadStore` | Persist upload sessions, chunks, and final SHA-256 validation. |
| `WebAuthnService` | Delegate registration and assertion ceremonies to an injected provider. |

## HTTP Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/admin/media/resumable` | Create a resumable upload session. |
| `GET` | `/admin/media/resumable/{upload_id}` | Read the current upload offset and expiry. |
| `PATCH` | `/admin/media/resumable/{upload_id}` | Upload a raw byte chunk using `Upload-Offset`. |
| `POST` | `/admin/media/resumable/{upload_id}/complete` | Validate and persist the completed upload. |
| `GET` | `/admin/media/folders` | List configured media folders. |
| `POST` | `/admin/media/folders` | Create a media folder with a CSRF header. |
| `DELETE` | `/admin/media/folders/{folder}` | Delete a folder and its stored files. |
| `POST` | `/admin/media/bulk` | Delete selected media names with a CSRF header. |
| `PATCH` | `/admin/media/{filename}` | Rename an asset or update allowed metadata. |
| `DELETE` | `/admin/media/{filename}` | Delete one asset with a CSRF header. |
| `GET` | `/admin/media/{filename}/signed-url` | Return a storage signed URL when the adapter supports it. |
| `GET` | `/admin/notifications/preferences` | Read the current user’s notification preferences. |
| `POST` | `/admin/notifications/preferences` | Update preferences with a CSRF header. |
| `GET` | `/admin/audit/verify` | Verify the persisted audit hash chain. |
| `POST` | `/admin/profile/webauthn/register/begin` | Start provider-backed credential registration. |
| `POST` | `/admin/profile/webauthn/register/finish` | Complete credential registration. |
| `POST` | `/admin/profile/webauthn/authenticate/begin` | Start provider-backed authentication. |
| `POST` | `/admin/profile/webauthn/authenticate/finish` | Verify an authentication assertion. |
| `GET` | `/admin/profile/trusted-devices` | List the signed-in user's trusted devices. |
| `POST` | `/admin/profile/trusted-devices` | Issue one opaque trusted-device token after MFA. |
| `DELETE` | `/admin/profile/trusted-devices/{device_id}` | Revoke one trusted device. |
| `POST` | `/admin/profile/mfa/recovery-codes` | Rotate MFA recovery codes and revoke trusted devices. |
| `GET` | `/admin/cms/api/scheduler/jobs` | Inspect durable scheduled-publication jobs. |
| `POST` | `/admin/cms/api/scheduler/jobs/{job_id}/retry` | Requeue a failed scheduled-publication job. |
| `GET` | `/admin/cms/api/media` | List reusable Admin media for CMS fields. |

All authenticated Admin mutations require the session cookie and
`X-CSRF-Token`. Use `redis_url` for shared sessions, rate limits, and
multi-worker coordination.

## Authorization

```python
from flaxon.admin import (
    AsyncAuthorizationProvider,
    CasbinAuthorizationProvider,
    DefaultAuthorizationProvider,
    PermissionCatalog,
    RedisPolicySynchronizer,
    default_group_definitions,
)
```

`PermissionCatalog` exposes readable definitions for model `view`, `add`,
`change`, and `delete` actions plus CMS capabilities. `DefaultAuthorizationProvider`
is dependency-free and supports legacy aliases during migration. Set
`strict_permissions=True` on `AdminDashboard` to require exact capabilities.
`CasbinAuthorizationProvider` is an optional adapter for an application-owned
PyCasbin enforcer; Casbin is not a Flaxon runtime dependency.

Use `default_group_definitions()` to seed the named `Administrator`, `Content
Editor`, `Publisher`, `Media Manager`, `Warehouse Staff`, `Support Agent`, and
`Read Only` groups. The legacy `staff` and `editor` names remain available for
migrations. A provider may implement async `has_permission`; Admin awaits it
at every protected request boundary. `RedisPolicySynchronizer` publishes
policy-change events and calls the enforcer's `load_policy()` in every worker.

## Optional production dependencies

Install the feature groups explicitly:

```shell
pip install "flaxon[admin,policy,scheduler]"
```

The `admin` group adds `nh3`, Pillow, `python-magic`, Argon2, and WebAuthn;
`policy` adds PyCasbin; `scheduler` adds APScheduler. `python-magic` also
requires the platform's libmagic runtime. `bandit` and `pip-audit` are part of
the development tools for CI security checks.

## Microservice control plane

The control plane is enabled by default when `AdminDashboard` is created. The
JSON API is rooted at `/admin/api/control-plane/` and the browser pages use
the same persistent records.

```python
from flaxon.admin import (
    AdminControlPlane,
    RemoteModelAdapter,
    RemoteServiceClient,
    ServiceRegistry,
)
```

::: flaxon.admin.ServiceRegistry
    options:
        members:
            - register
            - unregister
            - get
            - list
            - set_instance
            - instances
            - set_dependencies
            - dependencies

::: flaxon.admin.RemoteServiceClient
    options:
        members:
            - __init__
            - request
            - get
            - post
            - patch
            - delete

::: flaxon.admin.RemoteModelAdapter
    options:
        members:
            - get_instances
            - get_instance
            - create_instance
            - update_instance
            - delete_instance

::: flaxon.admin.AdminControlPlane
    options:
        members:
            - __init__
