#!/usr/bin/env python3
"""Vendor Tailwind CSS, Font Awesome and the Inter font so the admin works offline.

Downloads each package tarball from the npm registry, verifies it against the integrity
hash npm publishes for that version, and writes the files and license notices into
``src/flaxon/admin/static/admin/vendor/<package>``. A ``MANIFEST.json`` records where the
files came from and their SHA-256.

    python scripts/vendor_admin_assets.py                  # download + build all
    python scripts/vendor_admin_assets.py --check          # verify every vendored file
    python scripts/vendor_admin_assets.py tailwind --build # rebuild Tailwind CSS only

Tailwind CSS is built with the standalone CLI (no runtime JIT) scanning the admin
templates so only the classes actually used are included.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_STATIC = ROOT / "src" / "flaxon" / "admin" / "static" / "admin" / "vendor"
TEMPLATES_DIR = ROOT / "src" / "flaxon" / "admin" / "templates" / "admin"
REGISTRY = "https://registry.npmjs.org"
TIMEOUT = 120


@dataclass(frozen=True)
class Package:
    """One vendored npm package."""

    key: str
    npm_name: str
    version: str
    directory: Path
    #: tarball path -> vendored relative path
    files: dict[str, str] = field(default_factory=dict)


def _npm_metadata(npm_name: str, version: str) -> dict:
    """Fetch the package metadata npm publishes for *version*."""
    url = f"{REGISTRY}/{npm_name}/{version}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:  # noqa: S310
        return json.loads(resp.read())


def _download_tarball(npm_name: str, version: str, integrity: str, tarball_url: str) -> bytes:
    """Download and verify the package tarball."""
    with urllib.request.urlopen(tarball_url, timeout=TIMEOUT) as resp:  # noqa: S310
        data = resp.read()
    actual = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if actual != integrity:
        raise ValueError(
            f"Integrity mismatch for {npm_name}@{version}:\n  expected {integrity}\n  got    {actual}"
        )
    return data


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_entry(data: bytes) -> dict:
    return {"sha256": _sha256(data), "bytes": len(data)}


def _extract(data: bytes, mapping: dict[str, str], dest: Path) -> dict[str, dict]:
    """Extract *mapping* files from the tarball *data* into *dest*."""
    dest.mkdir(parents=True, exist_ok=True)
    result: dict[str, dict] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member_path, rel_path in mapping.items():
            # npm tarballs have a "package/" prefix
            candidates = [f"package/{member_path}", member_path]
            found = None
            for c in candidates:
                try:
                    tar.getmember(c)
                    found = c
                    break
                except KeyError:
                    continue
            if found is None:
                raise FileNotFoundError(f"{member_path} not found in tarball")
            f = tar.extractfile(found)
            if f is None:
                raise FileNotFoundError(f"{member_path} is not a file in tarball")
            content = f.read()
            out = dest / rel_path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(content)
            result[rel_path] = _file_entry(content)
    return result


# ---------------------------------------------------------------------------
# Font Awesome 6 Free (CSS + webfonts)
# ---------------------------------------------------------------------------

FONT_AWESOME = Package(
    key="font-awesome",
    npm_name="@fortawesome/fontawesome-free",
    version="6.6.0",
    directory=ADMIN_STATIC / "font-awesome",
    files={
        "css/all.min.css": "css/all.min.css",
        "LICENSE.txt": "LICENSE.txt",
    },
)


def _vendor_font_awesome(pkg: Package) -> dict:
    """Download Font Awesome and extract CSS + webfont files."""
    meta = _npm_metadata(pkg.npm_name, pkg.version)
    integrity = meta["dist"]["integrity"]
    tarball_url = meta["dist"]["tarball"]
    data = _download_tarball(pkg.npm_name, pkg.version, integrity, tarball_url)

    # Also extract all webfont files referenced by the CSS
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        webfont_names = [
            m.name for m in tar.getmembers() if m.name.startswith("package/webfonts/") and m.isfile()
        ]

    mapping = dict(pkg.files)
    for wf in webfont_names:
        rel = wf.replace("package/", "")
        mapping[wf.replace("package/", "")] = rel

    files = _extract(data, mapping, pkg.directory)

    manifest = {
        "name": pkg.npm_name,
        "version": pkg.version,
        "license": "OFL-1.1 (icons) / MIT (CSS/JS)",
        "source": tarball_url,
        "npm_integrity": integrity,
        "retrieved": datetime.now(UTC).strftime("%Y-%m-%d"),
        "files": files,
    }
    (pkg.directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Inter font (via @fontsource/inter)
# ---------------------------------------------------------------------------

INTER = Package(
    key="inter",
    npm_name="@fontsource/inter",
    version="5.1.1",
    directory=ADMIN_STATIC / "inter",
)


def _vendor_inter(pkg: Package) -> dict:
    """Download the Inter font and extract latin woff2 files, build a combined CSS."""
    meta = _npm_metadata(pkg.npm_name, pkg.version)
    integrity = meta["dist"]["integrity"]
    tarball_url = meta["dist"]["tarball"]
    data = _download_tarball(pkg.npm_name, pkg.version, integrity, tarball_url)

    # Extract only latin normal woff2 files for weights 300-800, plus LICENSE.
    weights = ["300", "400", "500", "600", "700", "800"]
    mapping: dict[str, str] = {"LICENSE": "LICENSE"}

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            name = m.name.replace("package/", "")
            if (
                name.startswith("files/")
                and name.endswith(".woff2")
                and "latin" in name
                and "-latin-" in name
                and "latin-ext" not in name
                and "italic" not in name
            ):
                weight_match = re.search(r"-latin-(\d{3})-normal\.woff2$", name)
                if weight_match and weight_match.group(1) in weights:
                    mapping[name] = name

    files = _extract(data, mapping, pkg.directory)

    # Build a combined @font-face CSS pointing at the local latin files.
    css_parts = ["/* Inter font, latin subset, weights 300-800. Vendored via @fontsource/inter. */\n"]
    for w in weights:
        css_parts.append(
            f"@font-face {{\n"
            f"  font-family: 'Inter';\n"
            f"  font-style: normal;\n"
            f"  font-display: swap;\n"
            f"  font-weight: {w};\n"
            f"  src: url(./files/inter-latin-{w}-normal.woff2) format('woff2');\n"
            f"}}\n"
        )

    combined = "\n".join(css_parts)
    (pkg.directory / "inter.css").write_text(combined, encoding="utf-8")
    files["inter.css"] = _file_entry(combined.encode())

    manifest = {
        "name": pkg.npm_name,
        "version": pkg.version,
        "license": "OFL-1.1",
        "source": tarball_url,
        "npm_integrity": integrity,
        "retrieved": datetime.now(UTC).strftime("%Y-%m-%d"),
        "files": files,
    }
    (pkg.directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Tailwind CSS (standalone CLI build)
# ---------------------------------------------------------------------------

TAILWIND = Package(
    key="tailwind",
    npm_name="tailwindcss",
    version="3.4.17",
    directory=ADMIN_STATIC / "tailwind",
)


def _vendor_tailwind(pkg: Package, build: bool = True) -> dict:
    """Download Tailwind CSS and build a production CSS from the admin templates."""
    meta = _npm_metadata(pkg.npm_name, pkg.version)
    integrity = meta["dist"]["integrity"]
    tarball_url = meta["dist"]["tarball"]
    data = _download_tarball(pkg.npm_name, pkg.version, integrity, tarball_url)

    # Extract the standalone CLI + license + package.json
    mapping = {
        "LICENSE": "LICENSE",
        "package.json": "package.json",
    }
    files = _extract(data, mapping, pkg.directory)

    if build:
        # Use npx to run the Tailwind CLI to build a production CSS
        # scanning the admin templates and existing CSS/JS
        input_css = pkg.directory / "input.css"
        input_css.write_text(
            "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
            encoding="utf-8",
        )

        content_paths = [
            str(TEMPLATES_DIR / "*.html"),
            str(ROOT / "src" / "flaxon" / "admin" / "static" / "admin" / "js" / "*.js"),
            str(ROOT / "src" / "flaxon" / "admin" / "static" / "admin" / "css" / "*.css"),
        ]

        cmd = [
            "npx",
            "--yes",
            f"tailwindcss@{pkg.version}",
            "--input",
            str(input_css),
            "--output",
            str(pkg.directory / "tailwind.min.css"),
            "--content",
            ",".join(content_paths),
            "--minify",
        ]
        print(f"  Building Tailwind CSS (scanning {len(content_paths)} content paths)...")
        result = subprocess.run(  # noqa: S603 - cmd is built from pinned args only
            cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT), check=False
        )
        if result.returncode != 0:
            print(f"  STDERR: {result.stderr[:500]}")
            raise RuntimeError(f"Tailwind build failed: {result.returncode}")

        built_css = (pkg.directory / "tailwind.min.css").read_bytes()
        files["tailwind.min.css"] = _file_entry(built_css)

        # Clean up input.css
        input_css.unlink()

    manifest = {
        "name": pkg.npm_name,
        "version": pkg.version,
        "license": "MIT",
        "source": tarball_url,
        "npm_integrity": integrity,
        "retrieved": datetime.now(UTC).strftime("%Y-%m-%d"),
        "build": "npx tailwindcss --minify (standalone CLI, content-scanned from admin templates)",
        "files": files,
    }
    (pkg.directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify() -> bool:
    """Re-check every file against its recorded SHA-256."""
    ok = True
    for pkg_dir in sorted(ADMIN_STATIC.iterdir()):
        manifest_path = pkg_dir / "MANIFEST.json"
        if not manifest_path.exists():
            print(f"  MISSING manifest: {pkg_dir}")
            ok = False
            continue
        manifest = json.loads(manifest_path.read_text())
        for rel, info in manifest.get("files", {}).items():
            f = pkg_dir / rel
            if not f.exists():
                print(f"  MISSING file: {f}")
                ok = False
                continue
            actual = _sha256(f.read_bytes())
            if actual != info["sha256"]:
                print(f"  MISMATCH: {f}")
                print(f"    expected {info['sha256']}")
                print(f"    got      {actual}")
                ok = False
            else:
                print(f"  OK: {rel} ({info['bytes']} bytes)")
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PACKAGES = {
    "font-awesome": ("fa", _vendor_font_awesome, FONT_AWESOME),
    "inter": ("inter", _vendor_inter, INTER),
    "tailwind": ("tw", _vendor_tailwind, TAILWIND),
}


def main() -> int:  # noqa: D103 - CLI entry point documented in module docstring
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "package",
        nargs="?",
        choices=[*list(PACKAGES), "all"],
        default="all",
    )
    parser.add_argument("--check", action="store_true", help="verify vendored files")
    parser.add_argument("--build", action="store_true", help="rebuild Tailwind CSS")
    args = parser.parse_args()

    if args.check:
        print("Verifying vendored admin assets...")
        return 0 if verify() else 1

    if args.package == "all":
        for name, (_, func, pkg) in PACKAGES.items():
            print(f"\n=== Vendoring {name} ({pkg.npm_name}@{pkg.version}) ===")
            manifest = func(pkg)
            print(f"  Done: {len(manifest['files'])} files")
        print("\n=== Verification ===")
        return 0 if verify() else 1

    _, func, pkg = PACKAGES[args.package]
    manifest = func(pkg, build=args.build) if args.package == "tailwind" else func(pkg)
    print(f"\nDone: {len(manifest['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
