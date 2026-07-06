#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "  claudeapikey First-Start Installer"
echo "========================================"
echo ""

# Check Python
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "Error: Python is not installed. Please install Python 3.10 or newer."
    exit 1
fi

PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python found: $PYTHON_CMD (version $PY_VERSION)"

# Check minimum Python version
MIN_VERSION="3.10"
if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "Error: Python $PY_VERSION is too old. Python $MIN_VERSION or newer is required."
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

warn() {
    echo "Warning: $*"
}

section() {
    echo ""
    echo "==> $*"
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local answer=""

    if [[ -t 0 ]]; then
        read -r -p "$prompt" answer || answer="$default"
    else
        printf "%s" "$prompt"
        read -r answer || answer="$default"
        echo "$answer"
    fi

    if [[ -z "$answer" ]]; then
        answer="$default"
    fi

    [[ "$answer" =~ ^[Yy]$ ]]
}

# Create isolated development virtual environment
VENV_DIR="$PROJECT_DIR/.claudeapikey"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR ..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip
section "Upgrading pip"
pip install --quiet --upgrade pip

# Install package in editable mode so the local source is used
# even if a system-wide claudeapikey is already present.
section "Installing claudeapikey"
pip install --quiet -e "$PROJECT_DIR"

# Check for claude
echo ""
if command -v claude &>/dev/null; then
    echo "Claude Code found: $(which claude)"
else
    warn "'claude' command not found in PATH."
    echo "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code/setup"
fi

# Initialize claudeapikey
section "Initializing claudeapikey"
claudeapikey install

section "Validating installed package path"
INSTALLED_PATH=$(python - <<PY
import pathlib
import claudeapikey

print(pathlib.Path(claudeapikey.__file__).resolve())
PY
)
case "$INSTALLED_PATH" in
    "$PROJECT_DIR"/*)
        echo "Using local editable package: $INSTALLED_PATH"
        ;;
    *)
        warn "claudeapikey is importing from outside this project: $INSTALLED_PATH"
        echo "Run again from this checkout, or inspect PATH/pip installation conflicts."
        ;;
esac

section "Checking vendor API keys"
MISSING_KEY_VENDORS=()
KEYRING_ERRORS=()
while IFS= read -r line; do
    if [[ "$line" == __KEYRING_ERROR__:* ]]; then
        KEYRING_ERRORS+=("${line#__KEYRING_ERROR__:}")
    elif [[ -n "$line" ]]; then
        MISSING_KEY_VENDORS+=("$line")
    fi
done < <(python - <<'PY'
from claudeapikey.config_store import load_config
from claudeapikey.secret_store import key_exists

for name in load_config().vendors:
    try:
        exists = key_exists(name)
    except Exception as exc:
        print(f"__KEYRING_ERROR__:{name}: {exc}")
        continue
    if not exists:
        print(name)
PY
)

if (( ${#KEYRING_ERRORS[@]} > 0 )); then
    warn "could not check some keyring entries:"
    for item in "${KEYRING_ERRORS[@]}"; do
        echo "  - $item"
    done
elif (( ${#MISSING_KEY_VENDORS[@]} == 0 )); then
    echo "All configured vendor keys are set."
else
    warn "missing API keys for: ${MISSING_KEY_VENDORS[*]}"
    if ask_yes_no "Set missing API keys now? (y/N): " "n"; then
        for vendor in "${MISSING_KEY_VENDORS[@]}"; do
            echo ""
            echo "Setting API key for '$vendor'. Type it into the terminal prompt."
            claudeapikey key set "$vendor"
        done
    else
        echo "Skipped key setup. Later, run: claudeapikey key set <vendor>"
    fi
fi

section "Checking and repairing saved proxy configuration"
python - <<'PY'
import re

from claudeapikey.config_store import get_config_path, load_config, save_config

config = load_config()
print(f"Config path: {get_config_path()}")
print(f"Proxy enabled: {'yes' if config.proxy_enabled else 'no'}")
print(f"Proxy URL: http://localhost:{config.proxy_port}")

ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
bracket_style_pattern = re.compile(r"\[[0-9;]*m\]")


def clean_value(value: str) -> str:
    value = ansi_pattern.sub("", value)
    value = bracket_style_pattern.sub("", value)
    return value.strip()


changes: list[str] = []
for name, profile in config.vendors.items():
    cleaned_model = clean_value(profile.model)
    if cleaned_model != profile.model:
        changes.append(f"vendor {name} model: {profile.model!r} -> {cleaned_model!r}")
        profile.model = cleaned_model

    cleaned_extra: dict[str, str] = {}
    for key, value in profile.extra_env.items():
        cleaned_key = key.strip()
        if cleaned_key.startswith("export "):
            cleaned_key = cleaned_key[len("export "):].strip()
        cleaned_value = clean_value(value)
        if cleaned_key != key or cleaned_value != value:
            changes.append(f"vendor {name} extra_env: {key!r} -> {cleaned_key!r}")
        cleaned_extra[cleaned_key] = cleaned_value
    profile.extra_env = cleaned_extra

for tier, model in config.proxy_tiers.items():
    cleaned_model = clean_value(model)
    if cleaned_model != model:
        changes.append(f"tier {tier}: {model!r} -> {cleaned_model!r}")
        config.proxy_tiers[tier] = cleaned_model

if changes:
    save_config(config)
    print("Repaired saved config:")
    for item in changes:
        print(f"  - {item}")
else:
    print("Saved proxy/vendor config looks clean.")

if config.proxy_enabled:
    print("Refreshing project-local Claude proxy settings ...")
PY

PROXY_ENABLED=$(python - <<'PY'
from claudeapikey.config_store import load_config
print("1" if load_config().proxy_enabled else "0")
PY
)
HAS_VENDORS=$(python - <<'PY'
from claudeapikey.config_store import load_config
print("1" if load_config().vendors else "0")
PY
)

if [[ "$PROXY_ENABLED" == "1" ]]; then
    claudeapikey proxy apply --local
    claudeapikey proxy status
elif [[ "$HAS_VENDORS" == "1" ]] && ask_yes_no "Enable multi-model proxy mode and apply local settings now? (Y/n): " "y"; then
    claudeapikey proxy enable --local
    PROXY_ENABLED="1"
else
    echo "Proxy mode is not enabled yet. Enable it with: claudeapikey proxy enable --local"
fi

section "Running diagnostics"
if ! claudeapikey doctor; then
    warn "doctor found setup issues. Fix the items above before using Claude Code."
fi

section "Checking localhost proxy port"
PROXY_PORT=$(python - <<'PY'
from claudeapikey.config_store import load_config
print(load_config().proxy_port)
PY
)
if python - "$PROXY_PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.5)
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
then
    echo "Local proxy/dashboard is reachable at http://127.0.0.1:$PROXY_PORT"
else
    warn "Nothing is listening on http://127.0.0.1:$PROXY_PORT"
    if [[ "$PROXY_ENABLED" == "1" ]] && ask_yes_no "Start proxy/dashboard in the background now? (Y/n): " "y"; then
        LOG_FILE="$VENV_DIR/serve.log"
        nohup claudeapikey serve --kill > "$LOG_FILE" 2>&1 &
        echo "Started proxy/dashboard in the background. Log: $LOG_FILE"
    else
        echo "Start it with: claudeapikey serve --kill"
    fi
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Quick start:"
# echo "  source .venv/bin/activate"
echo "make the .claudeapikey/bin directory available in your PATH"
export PATH="$PROJECT_DIR/.claudeapikey/bin:$PATH"
# Auto-source venv in new bash sessions (avoid duplicates)
SOURCE_LINE="source $PROJECT_DIR/.claudeapikey/bin/activate"
if [[ -f "$HOME/.bashrc" ]] && ! grep -Fxq "$SOURCE_LINE" "$HOME/.bashrc" 2>/dev/null; then
    echo "$SOURCE_LINE" >> "$HOME/.bashrc"
    echo "Added auto-source to ~/.bashrc"
fi

if ! ask_yes_no "Do you want to activate the venv in your current shell now? (Y/n): " "y"; then
    echo "Skipped. You can activate it later with:"
    echo "  source ~/.bashrc"
elif [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # Script is being sourced (e.g., source ./init.sh) — can modify current shell
    source "$HOME/.bashrc"
    echo "Activated! Your prompt should now show (claudeapikey)"
else
    # Script is being executed (./init.sh) — cannot modify parent shell
    echo ""
    echo "Please run this command in your current shell to activate now:"
    echo "  source ~/.bashrc"
fi
echo ""
echo "Then you can run commands like:"
echo "  claudeapikey add <vendor> --base-url <url> --model <model>"
echo "  claudeapikey key set <vendor>"
echo "  claudeapikey run <vendor>"
echo ""
echo "For multi-model proxy mode:"
echo "  claudeapikey proxy enable --local"
echo "  claudeapikey serve --kill"
echo "  claudeapikey proxy status"
echo "  claude"
echo ""
echo "See SETUP_FAILURE_PREVENTION.md for the checklist."
echo ""

