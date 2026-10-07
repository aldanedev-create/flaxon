"""Isolated fixtures for the expanded behavioral regression suite."""

import asyncio

import pytest

from flaxon.admin import AdminDashboard
from flaxon.admin.registry import Registry
from flaxon.admin.services import AdminAuth, AdminStore


@pytest.fixture
def auth():
    return AdminAuth(
        users=[
            {
                "username": "admin",
                "password": "Admin123!",
                "permissions": ["admin.superuser"],
                "email": "admin@example.com",
            },
            {
                "username": "reader",
                "password": "Reader123!",
                "permissions": ["admin.view_dashboard", "admin.manage_profile"],
            },
        ],
        strict_permissions=True,
    )


@pytest.fixture
def admin_store(tmp_path):
    return AdminStore(str(tmp_path / "admin.sqlite3"))


@pytest.fixture
def dashboard(app, admin_store, tmp_path):
    return AdminDashboard(
        app,
        store=admin_store,
        registry=Registry(),
        strict_permissions=True,
        upload_dir=str(tmp_path / "uploads"),
        users=[
            {
                "username": "admin",
                "password": "Admin123!",
                "permissions": ["admin.superuser"],
                "email": "admin@example.com",
            },
            {
                "username": "reader",
                "password": "Reader123!",
                "permissions": ["admin.view_dashboard", "admin.manage_profile"],
            },
        ],
    )


@pytest.fixture
def admin_headers(dashboard):
    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    return {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}


@pytest.fixture
def reader_headers(dashboard):
    token = asyncio.run(dashboard.auth.login("reader", "Reader123!"))
    return {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}
