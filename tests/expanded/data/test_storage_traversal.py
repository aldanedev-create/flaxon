"""Storage traversal behavior and boundary cases."""

import pytest

from flaxon.files.storage import FileStorage


@pytest.mark.parametrize("path", ["../outside.txt", "..\\outside.txt", "nested/../../outside.txt"])
def test_writes_cannot_escape_storage(tmp_path, path):
    storage = FileStorage(str(tmp_path / "uploads"))
    with pytest.raises(ValueError):
        storage.save_bytes(b"secret", path)
    assert not (tmp_path / "outside.txt").exists()


def test_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "uploads"
    outside = tmp_path / "outside"
    outside.mkdir()
    storage = FileStorage(str(root))
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        storage.save_bytes(b"secret", "file.txt", path="link")
    assert not (outside / "file.txt").exists()


def test_delete_cannot_remove_outside_file(tmp_path):
    outside = tmp_path / "keep.txt"
    outside.write_text("keep")
    assert not FileStorage(str(tmp_path / "uploads")).delete(str(outside))
    assert outside.read_text() == "keep"
