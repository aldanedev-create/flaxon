"""Uploaded file stream behavior and boundary cases."""

from io import BytesIO
from pathlib import Path

import pytest

from flaxon.files.upload import UploadedFile


@pytest.mark.asyncio
async def test_reads_respect_offset_and_seek():
    upload = UploadedFile("note.txt", "text/plain", 6, BytesIO(b"abcdef"))
    assert await upload.read(2) == b"ab"
    assert await upload.read(2) == b"cd"
    await upload.seek(0)
    assert await upload.read() == b"abcdef"


def test_save_rewinds_partially_read_file(tmp_path):
    stream = BytesIO(b"abcdef")
    stream.read(3)
    upload = UploadedFile("note.txt", "text/plain", 6, stream)
    destination = tmp_path / "saved.txt"
    upload.save(str(destination))
    assert Path(destination).read_bytes() == b"abcdef"


@pytest.mark.asyncio
async def test_close_releases_underlying_stream():
    stream = BytesIO(b"data")
    upload = UploadedFile("a", "text/plain", 4, stream)
    await upload.close()
    assert stream.closed
