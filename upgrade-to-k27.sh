#!/usr/bin/env bash
# Add or update a Kimi K2.7 Code vendor for claudeapikey.
# Run from the repo root: ./upgrade-to-k27.sh

set -euo pipefail

cd "$(dirname "$0")"

# ---------------------------------------------------------------------------
# Locate claudeapikey and a Python interpreter that can import it.
# ---------------------------------------------------------------------------
if command -v claudeapikey >/dev/null 2>&1; then
    CLI=claudeapikey
elif [ -x .claudeapikey/bin/claudeapikey ]; then
    CLI=.claudeapikey/bin/claudeapikey
else
    echo "Error: claudeapikey executable not found." >&2
    echo "Install the project first (see CLAUDE.md)." >&2
    exit 1
fi

if .claudeapikey/bin/python -c "import claudeapikey" >/dev/null 2>&1; then
    PY=.claudeapikey/bin/python
elif command -v python3 >/dev/null 2>&1 && python3 -c "import claudeapikey" >/dev/null 2>&1; then
    PY=python3
else
    echo "Error: Python with claudeapikey installed not found." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Back up the current config.
# ---------------------------------------------------------------------------
CONFIG_PATH="$($PY -c "from claudeapikey.config_store import get_config_path; print(get_config_path())")"
BACKUP_PATH="${CONFIG_PATH}.backup.$(date +%Y%m%d-%H%M%S)"
cp "$CONFIG_PATH" "$BACKUP_PATH"
echo "Config backed up to: $BACKUP_PATH"

# ---------------------------------------------------------------------------
# Configure the 'kimi-k27' vendor for K2.7 Code.
# ---------------------------------------------------------------------------
$PY - <<'PY'
from claudeapikey.config_store import load_config, save_config
from claudeapikey.models import VendorProfile
from claudeapikey.secret_store import get_key, key_exists, set_key

config = load_config()
vendor = "kimi-k27"
source_vendor = "kimi"

if vendor in config.vendors:
    profile = config.vendors[vendor]
    profile.base_url = "https://api.kimi.com/coding/"
    profile.auth_env = "ANTHROPIC_AUTH_TOKEN"
    profile.model = "kimi-for-coding"
    print("Updated existing vendor 'kimi-k27'.")
else:
    profile = VendorProfile(
        base_url="https://api.kimi.com/coding/",
        auth_env="ANTHROPIC_AUTH_TOKEN",
        model="kimi-for-coding",
    )
    config.vendors[vendor] = profile
    print("Created vendor 'kimi-k27'.")

profile.extra_env = {
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-for-coding",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-for-coding",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "kimi-for-coding",
    "ANTHROPIC_DEFAULT_FABLE_MODEL": "kimi-for-coding",
    "CLAUDE_CODE_SUBAGENT_MODEL": "kimi-for-coding",
    "ENABLE_TOOL_SEARCH": "false",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "262144",
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
}

save_config(config)

# Reuse the same API key from the main 'kimi' vendor if available.
if source_vendor in config.vendors and not key_exists(vendor):
    existing_key = get_key(source_vendor)
    if existing_key:
        set_key(vendor, existing_key)
        print(f"Copied API key from '{source_vendor}' to '{vendor}'.")
PY

# ---------------------------------------------------------------------------
# Make sure an API key is stored.
# ---------------------------------------------------------------------------
if ! $CLI key get kimi-k27 --raw >/dev/null 2>&1; then
    echo
    echo "Please enter your Kimi API key:"
    $CLI key set kimi-k27
fi

# ---------------------------------------------------------------------------
# Update proxy tiers and apply settings.
# ---------------------------------------------------------------------------
PROXY_ENABLED="$($PY -c "from claudeapikey.config_store import load_config; print(load_config().proxy_enabled)")"

if [ "$PROXY_ENABLED" = "True" ]; then
    $PY - <<'PY'
from claudeapikey.config_store import load_config, save_config
config = load_config()
if config.proxy_tiers:
    for tier in config.proxy_tiers:
        config.proxy_tiers[tier] = "kimi-for-coding"
    save_config(config)
    print("Proxy tiers updated to 'kimi-for-coding'.")
PY
    $CLI proxy apply --local
    echo
    echo "Proxy settings applied to ./.claude/settings.local.json."
    echo "Start the proxy before Claude Code: claudeapikey serve"
else
    $CLI use kimi-k27 --local
    echo
    echo "Direct-mode settings applied to ./.claude/settings.local.json."
    echo "Launch Claude Code with: claudeapikey run kimi-k27"
fi

echo
echo "Upgrade complete. Run 'claudeapikey doctor' to verify."
