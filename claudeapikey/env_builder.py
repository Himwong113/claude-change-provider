"""Build environment variables for running Claude Code with a vendor."""

from claudeapikey.config_store import load_config
from claudeapikey.models import VendorProfile
from claudeapikey.secret_store import get_key


def build_env(vendor_name: str) -> dict[str, str]:
    """Build a dictionary of environment variables for the given vendor.

    Raises:
        ValueError: If the vendor does not exist.
        RuntimeError: If the API key is missing.
    """
    config = load_config()
    profile = config.vendors.get(vendor_name)
    if profile is None:
        raise ValueError(f"Vendor '{vendor_name}' not found. Add it with: claudeapikey add {vendor_name}")

    key = get_key(vendor_name)
    if key is None:
        raise RuntimeError(
            f"API key for '{vendor_name}' not found. Set it with: claudeapikey key set {vendor_name}"
        )

    env: dict[str, str] = {}

    if profile.base_url:
        env["ANTHROPIC_BASE_URL"] = profile.base_url

    env[profile.auth_env] = key
    env["ANTHROPIC_MODEL"] = profile.model

    for k, v in profile.extra_env.items():
        env[k] = v

    return env


def build_env_exports(vendor_name: str) -> str:
    """Build shell export statements for the given vendor."""
    env = build_env(vendor_name)
    lines = []
    for k, v in env.items():
        # Simple shell-safe quoting
        escaped = v.replace("'", "'\"'\"'")
        lines.append(f"export {k}='{escaped}'")
    return "\n".join(lines)
