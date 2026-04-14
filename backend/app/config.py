import sys
from os import getenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _resolve_data_dir() -> Path:
    env_path = getenv("TRACKTECH_DATA_DIR")
    if env_path:
        return Path(env_path)

    if getattr(sys, "frozen", False):
        return Path.home() / ".tracktech_metainfo_updater" / "data"

    return ROOT_DIR / "data"


DATA_DIR = _resolve_data_dir()
BACKUP_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "metainfo.db"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "metainfo.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
}

WEBSOCKET_PING_SECONDS = 1.0
