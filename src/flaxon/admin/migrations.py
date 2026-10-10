"""Migration helpers for projects that store admin/CMS data in their database."""

from __future__ import annotations

import json
import time
from pathlib import Path

ADMIN_SCHEMA_UP = (
    "\nCREATE TABLE IF NOT EXISTS flaxon_admin_users (id VARCHAR(6"
    "4) PRIMARY KEY, username VARCHAR(150) NOT NULL UNIQUE, email"
    " VARCHAR(320), password_hash TEXT NOT NULL, roles TEXT NOT N"
    "ULL DEFAULT '[]', permissions TEXT NOT NULL DEFAULT '[]', ac"
    "tive BOOLEAN NOT NULL DEFAULT TRUE, metadata TEXT NOT NULL D"
    "EFAULT '{}');\nCREATE TABLE IF NOT EXISTS flaxon_admin_settin"
    "gs (key VARCHAR(150) PRIMARY KEY, value TEXT NOT NULL);\nCREA"
    "TE TABLE IF NOT EXISTS flaxon_admin_activity (id VARCHAR(64)"
    " PRIMARY KEY, action VARCHAR(100) NOT NULL, resource VARCHAR"
    "(150) NOT NULL, record_id VARCHAR(150), username VARCHAR(150"
    "), details TEXT NOT NULL DEFAULT '{}', created_at TIMESTAMP "
    "NOT NULL);\nCREATE TABLE IF NOT EXISTS flaxon_admin_store (na"
    "mespace VARCHAR(255) NOT NULL, key VARCHAR(255) NOT NULL, va"
    "lue TEXT NOT NULL, PRIMARY KEY(namespace, key));\nCREATE TABL"
    "E IF NOT EXISTS flaxon_admin_operations (id VARCHAR(64) PRIM"
    "ARY KEY, kind VARCHAR(80) NOT NULL, payload TEXT NOT NULL, c"
    "reated_at TIMESTAMP NOT NULL);\nCREATE TABLE IF NOT EXISTS fl"
    "axon_cms_taxonomies (id VARCHAR(64) PRIMARY KEY, name VARCHA"
    "R(150) NOT NULL, slug VARCHAR(180) NOT NULL UNIQUE, descript"
    "ion TEXT);\nCREATE TABLE IF NOT EXISTS flaxon_cms_terms (id V"
    "ARCHAR(64) PRIMARY KEY, taxonomy_id VARCHAR(64) NOT NULL, na"
    "me VARCHAR(150) NOT NULL, slug VARCHAR(180) NOT NULL, parent"
    "_id VARCHAR(64));\nCREATE TABLE IF NOT EXISTS flaxon_cms_comm"
    "ents (id VARCHAR(64) PRIMARY KEY, content_type VARCHAR(150) "
    "NOT NULL, record_id VARCHAR(150) NOT NULL, author_name VARCH"
    "AR(150), author_email VARCHAR(320), body TEXT NOT NULL, stat"
    "us VARCHAR(30) NOT NULL DEFAULT 'pending', created_at TIMEST"
    "AMP NOT NULL);\nCREATE TABLE IF NOT EXISTS flaxon_cms_menus ("
    "name VARCHAR(150) PRIMARY KEY, items TEXT NOT NULL DEFAULT '"
    "[]');\n"
)

ADMIN_SCHEMA_DOWN = (
    "\nDROP TABLE IF EXISTS flaxon_cms_menus; DROP TABLE IF EXISTS"
    " flaxon_cms_comments; DROP TABLE IF EXISTS flaxon_cms_terms;"
    " DROP TABLE IF EXISTS flaxon_cms_taxonomies; DROP TABLE IF E"
    "XISTS flaxon_admin_operations; DROP TABLE IF EXISTS flaxon_a"
    "dmin_store; DROP TABLE IF EXISTS flaxon_admin_activity; DROP"
    " TABLE IF EXISTS flaxon_admin_settings; DROP TABLE IF EXISTS"
    " flaxon_admin_users;\n"
)


def write_admin_migration(directory: str | Path = "migrations", name: str = "flaxon_admin") -> Path:
    """Generate a migration JSON file consumed by ``flaxon migrate``."""
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
