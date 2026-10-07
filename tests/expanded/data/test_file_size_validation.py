"""File size validation behavior and boundary cases."""

from io import BytesIO

import pytest

from flaxon.files.upload import UploadedFile
from flaxon.files.validation import FileValidator


@pytest.mark.parametrize("size,valid", [(0, False), (1, True), (10, True), (11, False)])
def test_size_boundaries_are_inclusive(size, valid):
    upload = UploadedFile("note.txt", "text/plain", size, BytesIO(b"x" * size))
    assert FileValidator(min_size=1, max_size=10).is_valid(upload) == valid


def test_many_validation_only_reports_invalid_indexes():
    files = [UploadedFile("a", "text/plain", 1, BytesIO()), UploadedFile("b", "text/plain", 20, BytesIO())]
    errors = FileValidator(max_size=10).validate_many(files)
    assert set(errors) == {"file_1"}
    assert "maximum" in errors["file_1"][0]


def test_mime_allowlist_rejects_unlisted_types():
    file = UploadedFile("a.html", "text/html", 1, BytesIO())
    assert not FileValidator(allowed_mime_types=["image/png"]).is_valid(file)
