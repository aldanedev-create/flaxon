"""scripts/vendor_docs_assets.py is what makes vendored code trustworthy, so test what it refuses."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def vendor():
    spec = importlib.util.spec_from_file_location(
        "vendor_docs_assets", ROOT / "scripts" / "vendor_docs_assets.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


def make_tarball(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_every_vendored_package_is_intact(vendor):
    assert set(vendor.PACKAGES) == {"redoc", "swagger-ui"}
    assert vendor.check() == 0


def test_a_tampered_tarball_is_refused(vendor):
    tarball = make_tarball({"package/anything": b"data"})
    good = "sha512-" + base64.b64encode(hashlib.sha512(tarball).digest()).decode()
    vendor.verify_integrity(tarball, good)  # the matching hash is accepted
    with pytest.raises(SystemExit, match="integrity"):
        vendor.verify_integrity(tarball + b"x", good)
    with pytest.raises(SystemExit, match="Unsupported integrity"):
        vendor.verify_integrity(tarball, "sha1-abc")


def test_downloads_only_from_the_npm_registry(vendor):
    with pytest.raises(SystemExit, match="unexpected host"):
        vendor.fetch("https://evil.example/redoc.tgz")
    with pytest.raises(SystemExit, match="unexpected host"):
        vendor.fetch("http://registry.npmjs.org/redoc/-/redoc-2.5.4.tgz")


@pytest.mark.parametrize(
    ("package", "version"),
    [
        ("redoc", "3.1.0"),
        ("redoc", "2.5"),
        ("redoc", "2.5.4-rc.1"),
        ("swagger-ui", "4.19.1"),
        ("swagger-ui", "6.0.0"),
    ],
)
def test_unsupported_versions_are_refused_before_any_download(vendor, package, version):
    with pytest.raises(SystemExit, match="only versions matching"):
        vendor.vendor(vendor.PACKAGES[package], version)


def test_extract_collects_licenses_and_the_hash_named_worker_notice(vendor):
    package = vendor.PACKAGES["redoc"]
    members = {name: name.encode() for name in package.files}
    members["package/bundles/0123abcd.worker.js.LICENSE.txt"] = b"worker notice"
    members["package/bundles/ignored.js.map"] = b"not wanted"
    files = vendor.extract(package, make_tarball(members))
    assert files["redoc.worker.js.LICENSE.txt"] == b"worker notice"
    assert "ignored.js.map" not in files
    assert set(files) == {*package.files.values(), "redoc.worker.js.LICENSE.txt"}


def test_extract_reports_missing_files_instead_of_vendoring_a_partial_set(vendor):
    package = vendor.PACKAGES["swagger-ui"]
    with pytest.raises(SystemExit, match="missing expected files"):
        vendor.extract(package, make_tarball({"package/swagger-ui.css": b"css"}))


def test_check_detects_a_modified_vendored_file(vendor, tmp_path, monkeypatch):
    source = vendor.PACKAGES["swagger-ui"]
    copy = tmp_path / "swagger_ui"
    copy.mkdir()
    for file in source.directory.iterdir():
        (copy / file.name).write_bytes(file.read_bytes())
    patched = type(source)(**{**source.__dict__, "directory": copy})
    assert vendor.check_package(patched) == []
    (copy / "swagger-ui.css").write_bytes(b"body{}")
    assert vendor.check_package(patched) == ["swagger-ui: swagger-ui.css does not match MANIFEST.json"]
