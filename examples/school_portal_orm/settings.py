"""Configuration shared by app.py and management.py. Secrets belong in .env."""
from pathlib import Path

from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR
DATA_DIR = BASE_DIR / "data"
env.load(BASE_DIR / ".env")

PROJECT_NAME = "northstar-academy-orm"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY", default="dev-only-northstar-secret-change-me-32ch")
ALLOWED_HOSTS = env.list("FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])
CSRF_TRUSTED_ORIGINS = env.list("FLAXON_CSRF_TRUSTED_ORIGINS", default=[])
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{DATA_DIR / 'school.sqlite3'}")
TIME_ZONE = "UTC"

ADMIN_ENABLED = True
CMS_ENABLED = True
ADMIN_SERVICES_ENABLED = False
# Staff accounts, sessions, CMS metadata and audit history live in the ORM too,
# so a single DATABASE_URL backs the whole portal. Set this before makemigrations.
ADMIN_STORE_BACKEND = "orm"
# Only used when ADMIN_STORE_BACKEND = "sqlite".
ADMIN_STORAGE_PATH = DATA_DIR / "admin.sqlite3"
