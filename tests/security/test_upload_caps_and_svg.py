"""Upload size/count caps are enforced, and SVG is not accepted as an untrusted image by default."""

from __future__ import annotations

import io

import pytest

from flaxon.exceptions import BadRequest
from flaxon.files.upload import FileUpload, UploadedFile
from flaxon.files.validation import ImageValidator


def _uploaded(data: bytes, name: str = "x.svg", mime: str = "image/svg+xml") -> UploadedFile:
    return UploadedFile(filename=name, content_type=mime, size=len(data), file=io.BytesIO(data))


def test_image_validator_rejects_svg_by_default():
    payload = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    file = _uploaded(payload)
    errors = ImageValidator().validate(file)
    assert any("svg" in e.lower() for e in errors), "SVG must not be accepted by default"


def test_image_validator_allows_svg_only_when_explicitly_enabled():
    payload = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    file = _uploaded(payload)
    assert ImageValidator(allow_svg=True).validate(file) == []


class _Request:
    def __init__(self, content_type: str, body: bytes):
        self.headers = {"content-type": content_type}
        self._body = body

    async def body(self):
        return self._body


def _multipart(files: list[tuple[str, bytes]]) -> tuple[str, bytes]:
    boundary = "TESTBOUND"
    chunks = []
    for name, content in files:
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
            + content
            + b"\r\n"
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}".encode().decode(), b"".join(chunks)


@pytest.mark.asyncio
async def test_file_upload_enforces_per_file_max_size():
    ct, body = _multipart([("f", b"x" * 5000)])
    upload = FileUpload(max_size=100, max_files=10)
    with pytest.raises(BadRequest, match="too large"):
        await upload.parse(_Request(ct, body))


@pytest.mark.asyncio
async def test_file_upload_enforces_max_files():
    ct, body = _multipart([(f"f{i}", b"x") for i in range(5)])
    upload = FileUpload(max_size=1000, max_files=2)
    with pytest.raises(BadRequest, match=r"(?i)too many"):
        await upload.parse(_Request(ct, body))
