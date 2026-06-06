"""Diagnostic checks for claudeapikey."""

import json
import shutil
from pathlib import Path

from claudeapikey.config_store import CONFIG_FILE, load_config
from claudeapikey.models import VendorProfile
from claudeapikey.secret_store import check_keyring_available, key_exists

LOCAL_SETTINGS = Path(".claude") / "settings.local.json"
GLOBAL_SETTINGS = Path.home() / ".claude" / "settings.json"


class CheckResult:
    def __init__(self):
        self.ok = True
        self.messages: list[tuple[str, str]] = []  # (status, detail)

    def add(self, status: str, detail: str) -> None:
        self.messages.append((status, detail))
        if status != "OK":
            self.ok = False


def run_doctor() -> CheckResult:
    """Run all diagnostic checks and return results."""
    result = CheckResult()

    # Check claude command
    if shutil.which("claude"):
        result.add("OK", "Claude command found")
    else:
        result.add("ERROR", "Claude command not found in PATH")

    # Check config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                json.load(f)
            result.add("OK", f"Config file valid ({CONFIG_FILE})")
        except json.JSONDecodeError as e:
            result.add("ERROR", f"Config file invalid JSON: {e}")
    else:
        result.add("WARN", f"Config file not found ({CONFIG_FILE})")

    # Check keyring
    if check_keyring_available():
        result.add("OK", "OS keyring available")
    else:
        result.add("WARN", "OS keyring not available")

    # Check vendors
    try:
        config = load_config()
    except Exception as e:
        result.add("ERROR", f"Failed to load config: {e}")
        return result

    if not config.vendors:
        result.add("WARN", "No vendors configured")
    else:
        for name, profile in config.vendors.items():
            errors = _validate_vendor(name, profile)
            if errors:
                result.add("ERROR", f"Vendor '{name}': {', '.join(errors)}")
            else:
                key_status = "key exists" if key_exists(name) else "key missing"
                extra = []
                if profile.base_url:
                    extra.append("base URL set")
                if profile.official:
                    extra.append("official")
                details = ", ".join([key_status] + extra)
                result.add("OK", f"Vendor '{name}': {details}")

    # Check Claude settings files
    for label, path in [("local", LOCAL_SETTINGS), ("global", GLOBAL_SETTINGS)]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
                result.add("OK", f"Claude {label} settings valid")
            except json.JSONDecodeError as e:
                result.add("ERROR", f"Claude {label} settings invalid: {e}")

    return result


def _validate_vendor(name: str, profile: VendorProfile) -> list[str]:
    errors = []
    if not profile.model:
        errors.append("missing model")
    if not profile.official and not profile.base_url:
        errors.append("missing base_url")
    if profile.auth_env not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        errors.append("invalid auth_env")
    return errors
