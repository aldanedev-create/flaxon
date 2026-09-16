from __future__ import annotations

import asyncio
from typing import ClassVar
from urllib.parse import urlencode

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard, Registry
from flaxon.admin.authorization import (
    CasbinAuthorizationProvider,
    DefaultAuthorizationProvider,
    PermissionCatalog,
    default_group_definitions,
)
from flaxon.http import HTMLResponse
from flaxon.testing import TestClient


class Product:
    items: ClassVar[dict[str, dict[str, str]]] = {
        "1": {"id": "1", "name": "Public", "owner": "editor"},
        "2": {"id": "2", "name": "Private", "owner": "other"},
    }

    @classmethod
    async def get_instances(cls):
        return list(cls.items.values())

    @classmethod
    async def get_instance(cls, object_id):
        return cls.items.get(str(object_id))


def test_catalog_and_strict_provider_require_exact_capabilities():
    catalog = PermissionCatalog()
    catalog.register_model("product", "Products")
    assert catalog.get("product.change_product").label == "Change Products"
    assert catalog.resolve("product:update") == "product.change_product"

    class User:
        username = "editor"
        id = "1"
        roles: ClassVar[list[str]] = []
        permissions: ClassVar[list[str]] = ["product.change_product"]

    provider = DefaultAuthorizationProvider(lambda: {}, strict=True)
    assert provider.has_permission(User(), "product.change_product")
    assert not provider.has_permission(User(), "product.delete_product")
    User.permissions = ["admin:write"]
    assert not provider.has_permission(User(), "product.delete_product")


def test_casbin_adapter_delegates_to_application_policy():
    class Enforcer:
        def enforce(self, subject, obj, action):
            return subject == "editor" and obj == "products" and action == "products.change_product"

    class User:
        username = "editor"
        id = "1"
        roles: ClassVar[list[str]] = []

    provider = CasbinAuthorizationProvider(Enforcer())
    assert provider.has_permission(User(), "products.change_product", resource="products")


def test_named_default_groups_keep_legacy_aliases_available():
    roles, descriptions = default_group_definitions(strict=True)
    assert {"administrator", "content_editor", "publisher", "media_manager", "warehouse_staff", "support_agent", "read_only"} <= roles.keys()
    assert "administrator" in descriptions
    legacy, _ = default_group_definitions(strict=False)
    assert "admin:write" in legacy["editor"]


def test_async_authorization_provider_is_awaited_at_request_boundary():
    class Provider:
        async def has_permission(self, user, permission, resource=None):
            await asyncio.sleep(0)
            return permission == "admin.view_dashboard"

    from flaxon.admin.services import AdminAuth

    auth = AdminAuth([{"username": "admin", "password": "Admin123!"}], permission_provider=Provider(), strict_permissions=True)
    user = auth.user("admin")
    assert asyncio.run(auth.has_permission_async(user, "admin.view_dashboard"))
    assert not auth.has_permission(user, "admin.view_dashboard")


def test_custom_admin_view_is_registered_without_overwriting_model_add_route():
    app = Flaxon("admin-custom-view")
    admin = AdminDashboard(
        app,
        strict_permissions=True,
        users=[{"username": "admin", "password": "Admin123!", "roles": ["administrator"]}],
    )

    async def reports(request):
        return HTMLResponse("reports")

    returned = admin.add_view(reports, "Reports", url="reports", methods={"GET", "POST"})
    assert returned is reports
    token = asyncio.run(admin.auth.login("admin", "Admin123!"))
    response = TestClient(app).get("/admin/reports", headers={"cookie": f"session_id={token}"})
    assert response.status_code == 200
    assert response.text == "reports"
    client = TestClient(app)
    assert client.post("/admin/reports", headers={"cookie": f"session_id={token}"}).status_code == 403
    assert client.post(
        "/admin/reports",
        headers={"cookie": f"session_id={token}", "x-csrf-token": admin.csrf_token()},
    ).status_code == 200


def test_strict_model_permissions_and_object_hooks_are_enforced():
    app = Flaxon("admin-exact-permissions")
    admin = AdminDashboard(
        app,
        registry=Registry(),
        strict_permissions=True,
        users=[{"username": "editor", "password": "Editor123!", "roles": ["editor"], "permissions": []}],
    )
    admin.register(
        Product,
        name="product",
        fields=["id", "name", "owner"],
        list_display=["id", "name", "owner"],
        can_view=lambda user, obj=None: obj is None or obj.get("owner") == user.username,
        can_change=lambda user, obj=None: obj is not None and obj.get("owner") == user.username,
    )
    admin.roles["editor"] = ["admin.view_dashboard", "product.view_product", "product.change_product"]
    admin.auth.role_permissions = admin.roles
    token = asyncio.run(admin.auth.login("editor", "Editor123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": admin.csrf_token()}
    client = TestClient(app)

    listing = client.get("/admin/product", headers=headers)
    assert listing.status_code == 200
    assert "Public" in listing.text and "Private" not in listing.text
    assert client.get("/admin/product/1/edit", headers=headers).status_code == 200
    assert client.get("/admin/product/2/edit", headers=headers).status_code == 403
    assert client.post("/admin/product/1/delete", headers=headers).status_code == 403
    assert client.get("/admin/users", headers=headers).status_code == 403


def test_roles_ui_saves_readable_permission_matrix_and_descriptions():
    app = Flaxon("admin-role-ui")
    admin = AdminDashboard(
        app,
        strict_permissions=True,
        users=[{"username": "admin", "password": "Admin123!", "roles": ["administrator"]}],
    )
    admin.register(Product, name="product")
    token = asyncio.run(admin.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": admin.csrf_token()}
    client = TestClient(app)

    page = client.get("/admin/roles", headers=headers)
    assert page.status_code == 200
    assert "View Products" in page.text
    body = urlencode({
        "_csrf": admin.csrf_token(),
        "action": "save",
        "name": "content-editors",
        "description": "Editors of product content",
        "permissions": ["admin.view_dashboard", "product.change_product"],
    }, doseq=True)
    saved = client.post(
        "/admin/roles",
        content=body,
        headers={**headers, "content-type": "application/x-www-form-urlencoded"},
    )
    assert saved.status_code == 200
    assert admin.roles["content-editors"] == ["admin.view_dashboard", "product.change_product"]
    assert admin.role_descriptions["content-editors"] == "Editors of product content"


def test_settings_only_persists_declared_custom_keys():
    app = Flaxon("admin-settings-allowlist")
    admin = AdminDashboard(
        app,
        config=AdminConfig(settings={"public_name": "Old"}),
        users=[{"username": "admin", "password": "Admin123!"}],
    )
    token = asyncio.run(admin.auth.login("admin", "Admin123!"))
    body = urlencode({"_csrf": admin.csrf_token(), "public_name": "New", "unexpected": "must-not-persist"})
    response = TestClient(app).post(
        "/admin/settings",
        content=body,
        headers={"cookie": f"session_id={token}", "content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert admin.config.settings == {"public_name": "New"}
