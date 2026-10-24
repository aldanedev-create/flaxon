"""Configuration for the Discord-clone example. Secrets live in .env only."""
from pathlib import Path

from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
env.load(BASE_DIR / ".env")

PROJECT_NAME = "discord-clone"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY", default="dev-only-discord-secret-change-me-32ch")
ALLOWED_HOSTS = env.list(
    "FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"]
)
CSRF_TRUSTED_ORIGINS = env.list("FLAXON_CSRF_TRUSTED_ORIGINS", default=[])
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{DATA_DIR / 'discord.sqlite3'}")
TIME_ZONE = "UTC"

# Redis is optional: only required for the multi-worker production topology.
REDIS_URL = env.str("REDIS_URL", default="")

ADMIN_ENABLED = True
CMS_ENABLED = True
ADMIN_SERVICES_ENABLED = False
ADMIN_STORE_BACKEND = "orm"
