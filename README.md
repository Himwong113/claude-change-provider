# claudeapikey

**Claude Code vendor switcher CLI.**

Switch between official Anthropic API, DeepSeek, Kimi, and other Claude-compatible providers with a single command. API keys are stored in your OS keyring — never written to shell rc files, `.env`, or Git-tracked config.

---

## Features

- **One-command vendor switching** — `claudeapikey run deepseek`
- **OS keyring storage** — API keys never touch disk in plain text
- **Web dashboard** — Manage vendors from a browser at `http://127.0.0.1:8787`
- **Systemd service** — Run the dashboard as a background user service
- **Claude settings integration** — Apply vendor configs to `~/.claude/settings.json` or `./.claude/settings.local.json`
- **Masked key display** — Keys are hidden as `sk-...abcd` unless `--raw` is used
- **Automatic backups** — Claude settings are backed up before any modification
- **Diagnostics** — Built-in `doctor` command checks your setup

---

## Installation

### From source (recommended for development)

```bash
git clone <repo>
cd claudeapikey
./init.sh
source .venv/bin/activate
```

`init.sh` will:
1. Check your Python version (3.10+ required)
2. Create a virtual environment in `.venv/`
3. Install dependencies
4. Run `claudeapikey install`

### With pipx (recommended for end users)

```bash
pipx install .
claudeapikey install
```

### With pip

```bash
pip install -e .
claudeapikey install
```

---

## Quick Start

```bash
# 1. Initialize
claudeapikey install

# 2. Add a vendor
claudeapikey add deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --auth-env ANTHROPIC_API_KEY \
  --model deepseek-v4-pro

# 3. Save the API key
claudeapikey key set deepseek

# 4. Run Claude Code with that vendor
claudeapikey run deepseek
```

---

## Vendor Setup Examples

### DeepSeek (Anthropic-compatible endpoint)

```bash
claudeapikey add deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --auth-env ANTHROPIC_API_KEY \
  --model deepseek-v4-pro

claudeapikey key set deepseek
claudeapikey run deepseek
```

### Kimi (via gateway)

```bash
claudeapikey add kimi \
  --base-url https://your-kimi-gateway.example.com \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --model kimi-k2

claudeapikey key set kimi
claudeapikey run kimi
```

### Official Anthropic API

```bash
claudeapikey add official \
  --official \
  --auth-env ANTHROPIC_API_KEY \
  --model sonnet

claudeapikey key set official
claudeapikey run official
```

### Outsource Provider

```bash
claudeapikey add outsource \
  --base-url https://provider.example.com \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --model provider-model-name

claudeapikey key set outsource
claudeapikey run outsource
```

---

## Command Reference

### Setup

| Command | Description |
|---------|-------------|
| `claudeapikey install` | Initialize config directory and check prerequisites |
| `claudeapikey uninstall` | Remove all vendors, keys, and config (destructive) |

### Vendor Management

| Command | Description |
|---------|-------------|
| `claudeapikey add <vendor>` | Add a new vendor profile |
| `claudeapikey edit <vendor>` | Edit an existing vendor profile |
| `claudeapikey list` | List all configured vendors |
| `claudeapikey show <vendor>` | Show detailed vendor info (key is masked) |
| `claudeapikey remove <vendor>` | Remove a vendor profile |

**Add flags:**
- `--base-url <url>` — API base URL (required for non-official vendors)
- `--auth-env ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN` — Which env var to use
- `--model <name>` — Model identifier
- `--official` — Mark as official Anthropic API (no base_url needed)
- `--extra-env KEY=VALUE` — Extra environment variables (repeatable)

### API Key Management

| Command | Description |
|---------|-------------|
| `claudeapikey key set <vendor>` | Interactively prompt for and save API key |
| `claudeapikey key set <vendor> --key <key>` | Save API key non-interactively |
| `claudeapikey key get <vendor>` | Show masked key |
| `claudeapikey key get <vendor> --raw` | Output raw key only (for automation / apiKeyHelper) |
| `claudeapikey key copy <vendor>` | Copy key to clipboard (requires `pyperclip`) |
| `claudeapikey key delete <vendor>` | Remove key from keyring |

### Running Claude Code

| Command | Description |
|---------|-------------|
| `claudeapikey run <vendor>` | Launch `claude` with the vendor's environment |
| `claudeapikey env <vendor>` | Print shell `export` statements |

`env` is useful when you want to apply settings manually:
```bash
eval "$(claudeapikey env deepseek)"
claude
```

### Claude Settings Integration

| Command | Description |
|---------|-------------|
| `claudeapikey use <vendor> --local` | Write vendor config to `./.claude/settings.local.json` |
| `claudeapikey use <vendor> --global` | Write vendor config to `~/.claude/settings.json` |
| `claudeapikey reset --local` | Remove managed fields from local settings |
| `claudeapikey reset --global` | Remove managed fields from global settings |
| `claudeapikey current` | Show the active vendor (if any) |

The `use` command writes settings with `apiKeyHelper` so Claude Code can fetch the key on demand — the raw key is **never** written to the settings file.

### Web Dashboard

| Command | Description |
|---------|-------------|
| `claudeapikey serve` | Start local web dashboard on `http://127.0.0.1:8787` |
| `claudeapikey serve --port 9999` | Start on a custom port |

The dashboard is bound to `127.0.0.1` only. It allows:
- Adding/editing/removing vendors
- Setting API keys
- Viewing masked keys
- Running diagnostics
- Viewing environment exports

### Systemd Service

| Command | Description |
|---------|-------------|
| `claudeapikey service install` | Install and enable the systemd user service |
| `claudeapikey service install --port 9999` | Install with a custom port |
| `claudeapikey service uninstall` | Remove the service |
| `claudeapikey service start` | Start the service now |
| `claudeapikey service stop` | Stop the service now |
| `claudeapikey service enable` | Enable auto-start on login |
| `claudeapikey service disable` | Disable auto-start on login |
| `claudeapikey service status` | Show installed/active/enabled state |

The service unit is installed to `~/.config/systemd/user/claudeapikey.service`.

### Diagnostics

| Command | Description |
|---------|-------------|
| `claudeapikey doctor` | Check claude binary, config, keyring, vendors, and settings |

---

## Security

- **API keys are stored in the OS keyring** via the `keyring` library. They are never written to:
  - `~/.bashrc` or `~/.zshrc`
  - `.env` files
  - `~/.claude/settings.json`
  - `./.claude/settings.local.json`
  - `config.json`
- **Masked by default** — Keys display as `sk-...abcd` in tables and normal output.
- **`--raw` flag** — Required to expose the full key. Intended for automation, `apiKeyHelper`, and `eval` usage only.
- **Settings backups** — Before editing Claude Code settings, a timestamped backup is created (e.g., `settings.json.claudeapikey-backup-20260606-153000`).
- **Config file permissions** — `config.json` is created with `0600` permissions.
- **Web dashboard** — Binds only to `127.0.0.1`. Full keys are never rendered in the UI.

---

## Configuration

Non-secret config is stored at:
```
~/.config/claudeapikey/config.json
```

Example:
```json
{
  "active_vendor": null,
  "vendors": {
    "deepseek": {
      "base_url": "https://api.deepseek.com/anthropic",
      "auth_env": "ANTHROPIC_API_KEY",
      "model": "deepseek-v4-pro",
      "official": false,
      "extra_env": {
        "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
      }
    }
  }
}
```

API keys are stored separately in the OS keyring under:
- **Service:** `claudeapikey`
- **Account:** `vendor:<vendor-name>`

---

## Troubleshooting

### `claude` command not found
```bash
claudeapikey doctor
```
Install Claude Code: https://docs.anthropic.com/en/docs/claude-code/setup

### Keyring not available (headless Linux)
Some Linux servers lack a graphical keyring backend. Install an alternative:
```bash
pip install keyrings.alt
```
Or use a secret service backend like `dbus-python`.

### Vendor add fails with "Non-official vendors must have a base_url"
You forgot `--base-url` for a non-official vendor. Either provide a base URL or use `--official`.

### `claudeapikey run` exits immediately
`run` uses `os.execvpe` to replace the current process with `claude`. If `claude` is missing, it prints an error and exits. Run `claudeapikey doctor` to verify.

---

## Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=claudeapikey

# Format / lint (optional)
black claudeapikey/ tests/
ruff check claudeapikey/ tests/
```

### Tech Stack

| Purpose | Package |
|---------|---------|
| CLI framework | Typer |
| Data validation | Pydantic v2 |
| Secret storage | keyring |
| Terminal UI | rich |
| Config paths | platformdirs |
| Web framework | FastAPI |
| HTTP server | Uvicorn |
| Templates | Jinja2 |
| Testing | pytest, httpx |

---

## License

MIT
