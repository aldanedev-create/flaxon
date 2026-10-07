"""Migration persistence behavior and boundary cases."""

from datetime import datetime

from flaxon.database.migrations import Migration, MigrationLoader


def test_roundtrip_preserves_dependencies_and_timestamps():
    migration = Migration(
        "001",
        "notes",
        "CREATE TABLE notes (id INT)",
        "DROP TABLE notes",
        ["000"],
        datetime(2026, 1, 1),
        datetime(2026, 1, 2),
    )
    assert Migration.from_dict(migration.to_dict()) == migration


def test_loader_sorts_versions_and_ignores_other_files(tmp_path):
    loader = MigrationLoader(str(tmp_path))
    loader.save_migration(Migration("002", "second", "SELECT 2"))
    loader.save_migration(Migration("001", "first", "SELECT 1"))
    (tmp_path / "README.md").write_text("documentation")
    assert [migration.version for migration in loader.load_migrations()] == ["001", "002"]


def test_missing_migration_directory_initializes_empty(tmp_path):
    path = tmp_path / "new"
    assert MigrationLoader(str(path)).load_migrations() == []
    assert path.is_dir()
