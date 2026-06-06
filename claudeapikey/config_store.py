"""Configuration file storage."""

import json
import os
from pathlib import Path

from platformdirs import user_config_dir

from claudeapikey.models import Config

CONFIG_DIR = Path(user_config_dir("claudeapikey", ensure_exists=True))
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config_path() -> Path:
    """Return the path to the config file."""
    return CONFIG_FILE


def load_config() -> Config:
    """Load configuration from disk. Returns default if missing."""
    if not CONFIG_FILE.exists():
        return Config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config.model_validate(data)


def save_config(config: Config) -> None:
    """Save configuration to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)
        f.write("\n")
    # Restrict permissions
    os.chmod(CONFIG_FILE, 0o600)


def config_exists() -> bool:
    """Check if the config file exists."""
    return CONFIG_FILE.exists()


def remove_config() -> None:
    """Remove the config file and directory."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    if CONFIG_DIR.exists() and not any(CONFIG_DIR.iterdir()):
        CONFIG_DIR.rmdir()
