"""Storage lifecycle behavior and boundary cases."""

from pathlib import Path

from flaxon.files.storage import FileStorage


def test_save_read_delete_and_missing_delete(tmp_path):
    storage = FileStorage(str(tmp_path / "uploads"))
    path = storage.save_bytes(b"hello", "hello.txt", path="documents")
    assert Path(path).read_bytes() == b"hello"
    assert storage.exists(path)
    assert storage.delete(path)
    assert not storage.exists(path)
    assert not storage.delete(path)


def test_generated_names_preserve_extensions_and_are_unique(tmp_path):
    storage = FileStorage(str(tmp_path))
    names = {storage.generate_filename("photo.png") for _ in range(20)}
    assert len(names) == 20
    assert all(name.endswith(".png") and "/" not in name for name in names)


def test_removing_one_directory_keeps_other_files(tmp_path):
    storage = FileStorage(str(tmp_path))
    storage.save_bytes(b"gone", "x.txt", path="first")
    kept = storage.save_bytes(b"keep", "x.txt", path="second")
    assert storage.delete_directory("first")
    assert storage.exists(kept)
