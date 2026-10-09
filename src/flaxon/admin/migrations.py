"""Migration helpers for projects that store admin/CMS data in their database."""

from __future__ import annotations

import time
from pathlib import Path

ADMIN_SCHEMA_UP = """
CREATE TABLE IF NOT EXISTS flaxon_admin_users (id VARCHAR(64) PRIMARY KEY, username VARCHAR(150) NOT NULL UNIQUE, email VARCHAR(320), password_hash TEXT NOT NULL, roles TEXT NOT NULL DEFAULT '[]', permissions TEXT NOT NULL DEFAULT '[]', active BOOLEAN NOT NULL DEFAULT TRUE, metadata TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS flaxon_admin_settings (key VARCHAR(150) PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_admin_activity (id VARCHAR(64) PRIMARY KEY, action VARCHAR(100) NOT NULL, resource VARCHAR(150) NOT NULL, record_id VARCHAR(150), username VARCHAR(150), details TEXT NOT NULL DEFAULT '{}', created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_admin_store (namespace VARCHAR(255) NOT NULL, key VARCHAR(255) NOT NULL, value TEXT NOT NULL, PRIMARY KEY(namespace, key));
CREATE TABLE IF NOT EXISTS flaxon_admin_operations (id VARCHAR(64) PRIMARY KEY, kind VARCHAR(80) NOT NULL, payload TEXT NOT NULL, created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_cms_taxonomies (id VARCHAR(64) PRIMARY KEY, name VARCHAR(150) NOT NULL, slug VARCHAR(180) NOT NULL UNIQUE, description TEXT);
CREATE TABLE IF NOT EXISTS flaxon_cms_terms (id VARCHAR(64) PRIMARY KEY, taxonomy_id VARCHAR(64) NOT NULL, name VARCHAR(150) NOT NULL, slug VARCHAR(180) NOT NULL, parent_id VARCHAR(64));
CREATE TABLE IF NOT EXISTS flaxon_cms_comments (id VARCHAR(64) PRIMARY KEY, content_type VARCHAR(150) NOT NULL, record_id VARCHAR(150) NOT NULL, author_name VARCHAR(150), author_email VARCHAR(320), body TEXT NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'pending', created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_cms_menus (name VARCHAR(150) PRIMARY KEY, items TEXT NOT NULL DEFAULT '[]');
"""

ADMIN_SCHEMA_DOWN = """
DROP TABLE IF EXISTS flaxon_cms_menus; DROP TABLE IF EXISTS flaxon_cms_comments; DROP TABLE IF EXISTS flaxon_cms_terms; DROP TABLE IF EXISTS flaxon_cms_taxonomies; DROP TABLE IF EXISTS flaxon_admin_operations; DROP TABLE IF EXISTS flaxon_admin_store; DROP TABLE IF EXISTS flaxon_admin_activity; DROP TABLE IF EXISTS flaxon_admin_settings; DROP TABLE IF EXISTS flaxon_admin_users;
"""


def write_admin_migration(directory: str | Path = "migrations", name: str = "flaxon_admin") -> Path:
    """Generate a migration JSON file consumed by ``flaxon migrate``."""
    import json

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    version = str(int(time.time() * 1000))
    path = directory / f"{version}_{name}.json"
    path.write_text(
        json.dumps(
            {"version": version, "name": name, "up": ADMIN_SCHEMA_UP, "down": ADMIN_SCHEMA_DOWN}, indent=2
        ),
        encoding="utf-8",
    )
    return path
