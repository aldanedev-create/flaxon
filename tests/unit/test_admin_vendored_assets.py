"""The admin ships its CSS, icons and fonts locally — no CDN, no runtime downloads.

Every claim here is checked against the actual files on disk so ``scripts/vendor_admin_assets.py``
and the templates cannot drift apart. Run ``python scripts/vendor_admin_assets.py --check`` to
verify the vendored files after any change.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.testing import TestClient

ROOT = Path(__file__).resolve().parents[2]
ADMIN = ROOT / "src" / "flaxon" / "admin"
TEMPLATES = ADMIN / "templates" / "admin"
VENDOR = ADMIN / "static" / "admin" / "vendor"

CDN_PATTERN = re.compile(
    r"https?://(?:cdn\.tailwindcss\.com|cdnjs\.cloudflare\.com|fonts\.googleapis\.com|"
    r"fonts\.gstatic\.com|unpkg\.com|cdn\.jsdelivr\.net)",
    re.IGNORECASE,
)


def _manifests() -> dict[str, dict]:
    return {
        d.name: json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
        for d in VENDOR.iterdir()
        if (d / "MANIFEST.json").exists()
    }


# --- no CDN references anywhere in the admin templates ------------------------


def test_admin_templates_reference_no_cdn():
    offenders: list[str] = []
    for template in sorted(TEMPLATES.glob("*.html")):
        for lineno, line in enumerate(template.read_text(encoding="utf-8").splitlines(), 1):
            if CDN_PATTERN.search(line):
                offenders.append(f"{template.name}:{lineno}: {line.strip()}")
    assert not offenders, "CDN assets found in admin templates:\n" + "\n".join(offenders)


def test_admin_templates_reference_the_vendored_assets():
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    cms = (TEMPLATES / "cms.html").read_text(encoding="utf-8")
    login = (TEMPLATES / "login.html").read_text(encoding="utf-8")

    assert "/static/admin/vendor/tailwind/tailwind.min.css" in base
    assert "/static/admin/vendor/font-awesome/css/all.min.css" in base
    assert "/static/admin/vendor/inter/inter.css" in base

    assert "/static/admin/vendor/tailwind/tailwind.min.css" in cms
    assert "/static/admin/vendor/font-awesome/css/all.min.css" in cms
    assert "/static/admin/vendor/inter/inter.css" in cms

    assert "/static/admin/vendor/font-awesome/css/all.min.css" in login
    assert "/static/admin/vendor/inter/inter.css" in login


# --- vendored files match their recorded hashes -------------------------------


def test_all_third_party_packages_are_vendored():
    assert set(_manifests()) == {"font-awesome", "inter", "tailwind"}


@pytest.mark.parametrize("package", ["font-awesome", "inter", "tailwind"])
def test_every_vendored_file_matches_its_recorded_sha256(package):
    manifest = _manifests()[package]
    pkg_dir = VENDOR / package
    assert manifest["files"], "manifest must list at least one file"
    for name, expected in manifest["files"].items():
        path = pkg_dir / name
        assert path.exists(), f"{package}/{name} is missing"
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected["sha256"], f"{package}/{name} was modified"
        assert len(data) == expected["bytes"], f"{package}/{name} size drift"


@pytest.mark.parametrize("package", ["font-awesome", "inter", "tailwind"])
def test_manifests_record_pinned_version_and_integrity(package):
    manifest = _manifests()[package]
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]), "version must be pinned"
    assert manifest["npm_integrity"].startswith("sha512-"), "npm integrity must be recorded"
    assert manifest["source"].startswith("https://registry.npmjs.org/")
    assert manifest["license"], "license must be recorded"


@pytest.mark.parametrize(
    ("package", "license_file"),
    [
        ("font-awesome", "LICENSE.txt"),
        ("inter", "LICENSE"),
        ("tailwind", "LICENSE"),
    ],
)
def test_license_files_travel_with_the_assets(package, license_file):
    assert (VENDOR / package / license_file).is_file()


# --- the vendored CSS actually provides the classes/icons/fonts the templates use ---


def test_tailwind_css_contains_the_classes_used_by_the_templates():
    css = (VENDOR / "tailwind" / "tailwind.min.css").read_text(encoding="utf-8")
    for cls in ("min-h-screen", "bg-slate-900", "flex", "grid", "rounded", "hidden", "md\\:block"):
        assert cls in css, f"Tailwind build is missing class {cls!r}"


def test_font_awesome_css_and_webfonts_are_present():
    css = (VENDOR / "font-awesome" / "css" / "all.min.css").read_text(encoding="utf-8")
    assert "@font-face" in css
    assert "fa-solid-900.woff2" in css
    assert (VENDOR / "font-awesome" / "webfonts" / "fa-solid-900.woff2").is_file()


def test_inter_css_declares_the_weights_the_templates_use():
    css = (VENDOR / "inter" / "inter.css").read_text(encoding="utf-8")
    for weight in (300, 400, 500, 600, 700, 800):
        assert f"font-weight: {weight};" in css
        assert f"inter-latin-{weight}-normal.woff2" in css
        assert (VENDOR / "inter" / "files" / f"inter-latin-{weight}-normal.woff2").is_file()


# --- packaged in the wheel ----------------------------------------------------


def test_vendored_assets_are_packaged():
    patterns = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]["package-data"][
        "flaxon"
    ]
    assert "admin/static/admin/vendor/**/*" in patterns


# --- the admin serves the vendored assets through its static mount ------------


def test_admin_serves_vendored_assets_without_a_cdn():
    """Exercise the full ASGI app (routes + static mount), not just file reads."""
    app = Flaxon("admin-assets", debug=True)
    AdminDashboard(app, users=[{"username": "admin", "password": "Admin123!"}])
    client = TestClient(app)

    assets = [
        "/static/admin/vendor/tailwind/tailwind.min.css",
        "/static/admin/vendor/font-awesome/css/all.min.css",
        "/static/admin/vendor/font-awesome/webfonts/fa-solid-900.woff2",
        "/static/admin/vendor/inter/inter.css",
        "/static/admin/vendor/inter/files/inter-latin-400-normal.woff2",
    ]
    for path in assets:
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
        assert len(response.content) > 0, f"{path} served empty body"
