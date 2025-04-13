from os import getenv
from pathlib import Path

__all__ = ["CONFIG_DIRECTORY", "CONFIG_FILE", "SESSION_FILE"]

CONFIG_DIRECTORY = Path(getenv("TELEGRAM_UPLOAD_CONFIG_DIRECTORY", "~/.config"))
CONFIG_FILE = Path(CONFIG_DIRECTORY).expanduser() / "telegram-upload.json"
SESSION_FILE = Path(CONFIG_DIRECTORY).expanduser() / "telegram-upload"
