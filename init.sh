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
echo "Upgrading pip ..."
pip install --quiet --upgrade pip

# Install package in editable mode so the local source is used
# even if a system-wide claudeapikey is already present.
echo "Installing claudeapikey ..."
pip install --quiet -e "$PROJECT_DIR"

# Check for claude
echo ""
if command -v claude &>/dev/null; then
    echo "Claude Code found: $(which claude)"
else
    echo "Warning: 'claude' command not found in PATH."
    echo "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code/setup"
fi

# Initialize claudeapikey
echo ""
echo "Initializing claudeapikey ..."
claudeapikey install

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

read -p "Do you want to activate the venv in your current shell now? (Y/n): " answer
if [[ "$answer" =~ ^[Nn]$ ]]; then
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
echo "Or start the web dashboard:"
echo "  claudeapikey serve"
echo ""

