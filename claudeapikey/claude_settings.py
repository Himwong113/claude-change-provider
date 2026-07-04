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

_TIER_ENV_MAP = {
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "subagent": "CLAUDE_CODE_SUBAGENT_MODEL",
}


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


def apply_proxy_settings(
    port: int = 8787,
    local: bool = False,
    global_: bool = False,
    default_model: str | None = None,
) -> None:
    """Configure Claude Code to send API requests through the local proxy."""
    if local and global_:
        raise ValueError("Cannot use both --local and --global")
    if not local and not global_:
        raise ValueError("Must specify --local or --global")

    path = LOCAL_SETTINGS if local else GLOBAL_SETTINGS
    data = _load_json(path)

    if path.exists():
        backup = _backup_path(path)
        shutil.copy2(path, backup)

    env: dict[str, str] = {
        "ANTHROPIC_BASE_URL": f"http://localhost:{port}",
        # Claude Code's client requires a key; the proxy ignores this value.
        "ANTHROPIC_API_KEY": "local-proxy",
    }

    config = load_config()
    model = default_model
    if model is None:
        model = config.proxy_tiers.get("default")
    if model is None:
        if config.active_vendor and config.active_vendor in config.vendors:
            model = config.vendors[config.active_vendor].model
        elif config.vendors:
            model = next(iter(config.vendors.values())).model

    if model:
        env["ANTHROPIC_MODEL"] = model
        data["model"] = model
    else:
        data.pop("model", None)

    for tier, mapped_model in config.proxy_tiers.items():
        env_var = _TIER_ENV_MAP.get(tier)
        if env_var:
            env[env_var] = mapped_model
        else:
            env[tier] = mapped_model

    data["env"] = env
    data.pop("apiKeyHelper", None)
    _save_json(path, data)


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

    if config.proxy_enabled:
        apply_proxy_settings(
            port=config.proxy_port,
            local=local,
            global_=global_,
            default_model=profile.model,
        )
        return

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
