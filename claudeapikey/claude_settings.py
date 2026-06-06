"""Read and write Claude Code settings files."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from claudeapikey.config_store import load_config
from claudeapikey.models import VendorProfile

LOCAL_SETTINGS = Path(".claude") / "settings.local.json"
GLOBAL_SETTINGS = Path.home() / ".claude" / "settings.json"

MANAGED_KEYS = {"model", "env", "apiKeyHelper"}


def _backup_path(path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return path.parent / f"{path.name}.claudeapikey-backup-{ts}"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def apply_vendor(vendor_name: str, local: bool = False, global_: bool = False) -> None:
    """Apply a vendor to Claude Code settings."""
    if local and global_:
        raise ValueError("Cannot use both --local and --global")
    if not local and not global_:
        raise ValueError("Must specify --local or --global")

    config = load_config()
    profile = config.vendors.get(vendor_name)
    if profile is None:
        raise ValueError(f"Vendor '{vendor_name}' not found")

    path = LOCAL_SETTINGS if local else GLOBAL_SETTINGS
    data = _load_json(path)

    # Backup existing file
    if path.exists():
        backup = _backup_path(path)
        shutil.copy2(path, backup)

    # Build managed settings
    env: dict[str, str] = {}
    if profile.base_url:
        env["ANTHROPIC_BASE_URL"] = profile.base_url
    env["ANTHROPIC_MODEL"] = profile.model
    for k, v in profile.extra_env.items():
        env[k] = v

    data["model"] = profile.model
    data["env"] = env
    data["apiKeyHelper"] = f"claudeapikey key get {vendor_name} --raw"

    _save_json(path, data)


def reset_settings(local: bool = False, global_: bool = False) -> None:
    """Remove managed fields from Claude Code settings."""
    if local and global_:
        raise ValueError("Cannot use both --local and --global")
    if not local and not global_:
        raise ValueError("Must specify --local or --global")

    path = LOCAL_SETTINGS if local else GLOBAL_SETTINGS
    if not path.exists():
        return

    data = _load_json(path)

    # Backup
    backup = _backup_path(path)
    shutil.copy2(path, backup)

    for key in MANAGED_KEYS:
        data.pop(key, None)

    _save_json(path, data)
