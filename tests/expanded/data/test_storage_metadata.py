"""Storage metadata behavior and boundary cases."""

from flaxon.files.storage import FileStorage


def test_metadata_matches_bytes_and_url_prefix(tmp_path):
    storage = FileStorage(str(tmp_path), url_prefix="/media")
    path = storage.save_bytes("Zoë".encode(), "note.txt", path="notes")
    info = storage.get_file_info(path)
    assert info["size"] == 4
    assert info["name"] == "note.txt" and info["extension"] == ".txt"
    assert storage.get_url(path) == "/media/notes/note.txt"
    assert storage.get_size(path) == 4


def test_listing_is_local_and_excludes_directories(tmp_path):
    storage = FileStorage(str(tmp_path))
    first = storage.save_bytes(b"a", "a.txt")
    storage.save_bytes(b"b", "b.txt", path="nested")
    assert storage.list_files() == [first]
    assert storage.list_files("missing") == []


def test_missing_metadata_and_size_have_empty_defaults(tmp_path):
    storage = FileStorage(str(tmp_path))
    assert storage.get_file_info("missing") == {}
    assert storage.get_size("missing") == 0
