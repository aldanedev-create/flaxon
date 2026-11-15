#!/usr/bin/env python3
"""Vendor the pinned ReDoc and Swagger UI releases so the interactive docs work offline.

Downloads the package tarball from the npm registry, verifies it against the integrity hash npm
publishes for that version, and writes the files and their license notices into
``src/flaxon/openapi/assets/<package>``. A ``MANIFEST.json`` records where the files came from
and their SHA-256, and the ``*_VERSION`` constant in the Python module is updated to match.

    python scripts/vendor_docs_assets.py redoc --version 2.5.4
    python scripts/vendor_docs_assets.py swagger-ui --version 5.35.0
    python scripts/vendor_docs_assets.py --check          # verify every vendored file

ReDoc 3.x is not supported: its standalone bundle is an ES module, which cannot be loaded with a
plain ``<script>`` tag.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "src" / "flaxon" / "openapi"
REGISTRY = "https://registry.npmjs.org"
TIMEOUT = 60


@dataclass(frozen=True)
class Package:
    """One vendored npm package."""

    key: str
    npm_name: str
    version_pattern: str
    directory: Path
    module: Path
    constant: str
    bundle: str
    #: tarball path -> vendored file name
    files: dict[str, str]
    #: (tarball path regex, vendored file name) for files whose name contains a build hash
    patterns: tuple[tuple[re.Pattern[str], str], ...] = field(default=())

    @property
    def manifest(self) -> Path:
        """Where the manifest recording the files' provenance and checksums lives."""
        return self.directory / "MANIFEST.json"


PACKAGES = {
    package.key: package
    for package in (
        Package(
            key="redoc",
            npm_name="redoc",
            version_pattern=r"2\.\d+\.\d+",
            directory=OPENAPI / "assets" / "redoc",
            module=OPENAPI / "redoc.py",
            constant="REDOC_VERSION",
            bundle="redoc.standalone.js",
            files={
                "package/bundles/redoc.standalone.js": "redoc.standalone.js",
                "package/bundles/redoc.standalone.js.LICENSE.txt": "redoc.standalone.js.LICENSE.txt",
                "package/LICENSE": "LICENSE",
            },
            patterns=(
                (
                    re.compile(r"package/bundles/[0-9a-f]+\.worker\.js\.LICENSE\.txt"),
                    "redoc.worker.js.LICENSE.txt",
                ),
            ),
        ),
        Package(
            key="swagger-ui",
            npm_name="swagger-ui-dist",
            version_pattern=r"5\.\d+\.\d+",
            directory=OPENAPI / "assets" / "swagger_ui",
            module=OPENAPI / "swagger.py",
            constant="SWAGGER_UI_VERSION",
            bundle="swagger-ui-bundle.js",
            files={
                "package/swagger-ui-bundle.js": "swagger-ui-bundle.js",
                "package/swagger-ui-bundle.js.LICENSE.txt": "swagger-ui-bundle.js.LICENSE.txt",
                "package/swagger-ui.css": "swagger-ui.css",
                "package/LICENSE": "LICENSE",
                "package/NOTICE": "NOTICE",
            },
        ),
    )
}


def fetch(url: str) -> bytes:
    """Download a URL from the npm registry."""
    if not url.startswith(f"{REGISTRY}/"):
        raise SystemExit(f"Refusing to download from an unexpected host: {url}")
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:  # noqa: S310 - host checked above
        return bytes(response.read())


def sha256(data: bytes) -> str:
    """Return the hex SHA-256 digest of the data."""
    return hashlib.sha256(data).hexdigest()


def verify_integrity(tarball: bytes, integrity: str) -> None:
    """Check the tarball against npm's ``sha512-<base64>`` integrity string."""
    algorithm, _, expected = integrity.partition("-")
    if algorithm != "sha512":
        raise SystemExit(f"Unsupported integrity algorithm: {algorithm}")
    if base64.b64encode(hashlib.sha512(tarball).digest()).decode() != expected:
        raise SystemExit("Tarball does not match npm's published integrity hash; refusing to vendor it.")


def extract(package: Package, tarball: bytes) -> dict[str, bytes]:
    """Pull the wanted files out of the npm tarball."""
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        for member in archive.getmembers():
            target = package.files.get(member.name)
            for pattern, name in package.patterns:
                if pattern.fullmatch(member.name):
                    target = name
            if target and member.isfile():
                handle = archive.extractfile(member)
                if handle is None:
                    raise SystemExit(f"Could not read {member.name}")
                files[target] = handle.read()
    wanted = {*package.files.values(), *(name for _, name in package.patterns)}
    if missing := wanted - set(files):
        raise SystemExit(f"Tarball is missing expected files: {sorted(missing)}")
    return files


def set_constant(package: Package, version: str) -> None:
    """Point the module's pinned-version constant at the vendored version."""
    source = package.module.read_text(encoding="utf-8")
    updated = re.sub(rf'(?m)^{package.constant} = "[^"]+"$', f'{package.constant} = "{version}"', source)
    if updated != source:
        package.module.write_text(updated, encoding="utf-8")


def vendor(package: Package, version: str) -> None:
    """Download, verify and write the vendored files for one release."""
    if not re.fullmatch(package.version_pattern, version):
        raise SystemExit(f"{package.key}: only versions matching {package.version_pattern} are supported.")
    metadata = json.loads(fetch(f"{REGISTRY}/{package.npm_name}/{version}"))
    tarball_url, integrity = metadata["dist"]["tarball"], metadata["dist"]["integrity"]
    tarball = fetch(tarball_url)
    verify_integrity(tarball, integrity)
    files = extract(package, tarball)
    if b"import.meta" in files[package.bundle]:
        raise SystemExit("This bundle uses import.meta and cannot be loaded as a classic script.")
    package.directory.mkdir(parents=True, exist_ok=True)
    for stale in package.directory.iterdir():
        if stale.is_file():
            stale.unlink()
    for name, data in files.items():
        (package.directory / name).write_bytes(data)
    manifest = {
        "name": package.npm_name,
        "version": version,
        "license": metadata.get("license", "unknown"),
        "source": tarball_url,
        "npm_integrity": integrity,
        "retrieved": datetime.now(UTC).date().isoformat(),
        "files": {name: {"sha256": sha256(data), "bytes": len(data)} for name, data in sorted(files.items())},
    }
    package.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    set_constant(package, version)
    bundle = files[package.bundle]
    summary = f"{package.bundle} {len(bundle):,} bytes, sha256 {sha256(bundle)}"
    print(f"Vendored {package.npm_name} {version}: {summary}")


def check_package(package: Package) -> list[str]:
    """Return the problems found with one vendored package (empty when it is intact)."""
    if not package.manifest.is_file():
        return [f"{package.key}: missing MANIFEST.json"]
    manifest = json.loads(package.manifest.read_text(encoding="utf-8"))
    problems: list[str] = []
    for name, expected in manifest["files"].items():
        path = package.directory / name
        if not path.is_file():
            problems.append(f"{package.key}: missing {name}")
        elif sha256(path.read_bytes()) != expected["sha256"]:
            problems.append(f"{package.key}: {name} does not match MANIFEST.json")
    pinned = re.search(rf'(?m)^{package.constant} = "([^"]+)"$', package.module.read_text(encoding="utf-8"))
    if not pinned or pinned.group(1) != manifest["version"]:
        problems.append(f"{package.key}: {package.constant} does not match MANIFEST.json")
    return problems


def check() -> int:
    """Verify every vendored package against its manifest."""
    problems = [problem for package in PACKAGES.values() for problem in check_package(package)]
    for problem in problems:
        print(f"ERROR: {problem}", file=sys.stderr)
    if not problems:
        for package in PACKAGES.values():
            version = json.loads(package.manifest.read_text(encoding="utf-8"))["version"]
            print(f"OK: {package.npm_name} {version} matches its manifest.")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("package", nargs="?", choices=sorted(PACKAGES), help="Which package to vendor")
    parser.add_argument("--version", help="Version to vendor, for example 2.5.4")
    parser.add_argument(
        "--check", action="store_true", help="Verify the vendored files against their manifests"
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()
    if not args.package or not args.version:
        parser.error("pass a package and --version X.Y.Z to vendor a release, or --check to verify")
    vendor(PACKAGES[args.package], args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
