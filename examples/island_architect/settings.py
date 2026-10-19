"""Configuration shared by app.py and management.py. Secrets belong in .env."""
from pathlib import Path

from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR
DATA_DIR = BASE_DIR / "data"
env.load(BASE_DIR / ".env")

PROJECT_NAME = "island-architect"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY", default="dev-only-island-secret-change-me-32chars")
ALLOWED_HOSTS = env.list("FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])
CSRF_TRUSTED_ORIGINS = env.list("FLAXON_CSRF_TRUSTED_ORIGINS", default=[])
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{DATA_DIR / 'island.sqlite3'}")
TIME_ZONE = "UTC"

# This example is deliberately small: no Admin, no CMS, one table. Point
# ADMIN_ENABLED at True and read docs/guides/orm-admin-custom-pages.md if you
# want staff accounts and a CRUD UI for the designs table.
ADMIN_ENABLED = False
CMS_ENABLED = False
