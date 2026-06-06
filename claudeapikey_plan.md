# `claudeapikey` — Claude Code Vendor Switcher

## 1. Purpose

`claudeapikey` is a focused CLI tool for switching Claude Code between different API vendors with one easy command.

The target daily workflow is:

```bash
claudeapikey run deepseek
claudeapikey run kimi
claudeapikey run outsource
claudeapikey run official
```

The tool is not meant to be a general API key manager for every application. Its first version should focus only on making Claude Code setup and vendor switching easier.

---

## 2. Core idea

Claude Code can be launched with different environment variables. `claudeapikey` stores vendor profiles and API keys, then launches Claude Code with the correct environment for the selected vendor.

Example:

```bash
claudeapikey run deepseek
```

Internally, this does something like:

```bash
ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" \
ANTHROPIC_API_KEY="saved-key-from-secret-store" \
ANTHROPIC_MODEL="deepseek-v4-pro" \
claude --model deepseek-v4-pro
```

For a gateway or outsource provider using bearer authentication:

```bash
ANTHROPIC_BASE_URL="https://provider.example.com" \
ANTHROPIC_AUTH_TOKEN="saved-key-from-secret-store" \
ANTHROPIC_MODEL="provider-model-name" \
claude --model provider-model-name
```

---

## 3. Final naming

Use only one public command:

```bash
claudeapikey
```

Do not use `ccv`.

---

## 4. Main command structure

```text
claudeapikey
├── install
├── add
├── edit
├── list
├── show
├── remove
├── key set
├── key delete
├── key copy
├── env
├── run
├── use --local
├── use --global
├── reset --local
├── reset --global
├── current
├── doctor
└── uninstall
```

---

## 5. Main user flows

### 5.1 Install

```bash
claudeapikey install
```

The install command should:

```text
1. Check whether `claude` exists in PATH.
2. Create the config folder.
3. Initialize the config file if missing.
4. Check whether the OS keyring is available.
5. Print the next recommended commands.
```

Example output:

```text
Claude API Key Manager

Claude Code found: yes
Config path: ~/.config/claudeapikey/config.json
Secret store: OS keyring

Done.

Next:
  claudeapikey add deepseek
  claudeapikey key set deepseek
  claudeapikey run deepseek
```

---

### 5.2 Add DeepSeek

```bash
claudeapikey add deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --auth-env ANTHROPIC_API_KEY \
  --model deepseek-v4-pro
```

Then save the key:

```bash
claudeapikey key set deepseek
```

Then run Claude Code:

```bash
claudeapikey run deepseek
```

---

### 5.3 Add Kimi

```bash
claudeapikey add kimi \
  --base-url https://your-kimi-gateway.example.com \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --model kimi-k2
```

```bash
claudeapikey key set kimi
claudeapikey run kimi
```

---

### 5.4 Add outsource provider

```bash
claudeapikey add outsource \
  --base-url https://provider.example.com \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --model provider-model-name
```

```bash
claudeapikey key set outsource
claudeapikey run outsource
```

---

### 5.5 Add official Anthropic

```bash
claudeapikey add official \
  --official \
  --auth-env ANTHROPIC_API_KEY \
  --model sonnet
```

```bash
claudeapikey key set official
claudeapikey run official
```

---

## 6. Vendor profile model

Store non-secret vendor configuration in:

```text
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
    },
    "kimi": {
      "base_url": "https://your-kimi-gateway.example.com",
      "auth_env": "ANTHROPIC_AUTH_TOKEN",
      "model": "kimi-k2",
      "official": false,
      "extra_env": {
        "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
      }
    },
    "official": {
      "base_url": null,
      "auth_env": "ANTHROPIC_API_KEY",
      "model": "sonnet",
      "official": true,
      "extra_env": {}
    }
  }
}
```

The real API keys should not be stored in this config file.

---

## 7. Secret storage

Use the OS keyring for real API keys.

Recommended Python package:

```text
keyring
```

Secret naming format:

```text
Service: claudeapikey
Username: vendor:<vendor-name>
Password: actual API key
```

Example:

```text
Service: claudeapikey
Username: vendor:deepseek
Password: sk-xxxx
```

Do not store raw keys in:

```text
~/.bashrc
~/.zshrc
~/.claude/settings.json
./.claude/settings.local.json
.env files
Git-tracked files
```

---

## 8. Environment generation rules

### 8.1 Official Anthropic

For official Anthropic API usage:

```bash
export ANTHROPIC_API_KEY="..."
export ANTHROPIC_MODEL="sonnet"
```

Optional launch:

```bash
claude --model sonnet
```

---

### 8.2 Anthropic-compatible gateway

For DeepSeek, Kimi, LiteLLM, or outsource provider through a Claude-compatible gateway:

```bash
export ANTHROPIC_BASE_URL="https://provider.example.com"
export ANTHROPIC_AUTH_TOKEN="..."
export ANTHROPIC_MODEL="provider-model-name"
```

Optional:

```bash
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY="1"
```

Launch:

```bash
claude --model provider-model-name
```

---

### 8.3 DeepSeek-style Anthropic endpoint

Some providers may instruct users to use:

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_API_KEY="..."
export ANTHROPIC_MODEL="deepseek-v4-pro"
```

So `claudeapikey` must not hardcode only one auth variable. Each vendor profile must choose either:

```text
ANTHROPIC_API_KEY
```

or:

```text
ANTHROPIC_AUTH_TOKEN
```

---

## 9. `claudeapikey run`

Command:

```bash
claudeapikey run deepseek
```

Behavior:

```text
1. Load the `deepseek` vendor profile.
2. Read the API key from OS keyring.
3. Build a clean environment for Claude Code.
4. Set ANTHROPIC_BASE_URL if the vendor has a base URL.
5. Set either ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN.
6. Set ANTHROPIC_MODEL.
7. Add any extra environment variables.
8. Execute `claude --model <model>`.
```

Important: this should not permanently modify the user’s shell files.

---

## 10. `claudeapikey env`

Command:

```bash
claudeapikey env deepseek
```

Output:

```bash
export ANTHROPIC_BASE_URL='https://api.deepseek.com/anthropic'
export ANTHROPIC_API_KEY='saved-key'
export ANTHROPIC_MODEL='deepseek-v4-pro'
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY='1'
```

Usage:

```bash
eval "$(claudeapikey env deepseek)"
claude
```

This is useful when the user wants to run Claude Code manually after applying the environment.

---

## 11. `claudeapikey use --local`

Command:

```bash
claudeapikey use deepseek --local
```

This should write project-local Claude Code settings to:

```text
./.claude/settings.local.json
```

This is useful when one project should always use a specific vendor.

Recommended generated settings:

```json
{
  "model": "deepseek-v4-pro",
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_MODEL": "deepseek-v4-pro",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
  },
  "apiKeyHelper": "claudeapikey key get deepseek --raw"
}
```

The key itself should not be written into the settings file.

---

## 12. `claudeapikey use --global`

Command:

```bash
claudeapikey use official --global
```

This should write user-level Claude Code settings to:

```text
~/.claude/settings.json
```

Use this only for the user’s default global vendor.

Recommended generated settings:

```json
{
  "model": "sonnet",
  "env": {
    "ANTHROPIC_MODEL": "sonnet"
  },
  "apiKeyHelper": "claudeapikey key get official --raw"
}
```

---

## 13. `apiKeyHelper` strategy

`apiKeyHelper` should return the selected vendor key from the OS keyring.

Example command:

```bash
claudeapikey key get deepseek --raw
```

Expected output:

```text
sk-xxxx
```

Rules:

```text
1. `--raw` prints only the key and nothing else.
2. No labels.
3. No extra newline beyond normal stdout behavior.
4. No masking.
5. No logging.
6. Fail with non-zero exit code if the key is missing.
```

This is important because Claude Code will call the helper and expect the credential value.

---

## 14. `claudeapikey doctor`

Command:

```bash
claudeapikey doctor
```

Checks:

```text
1. `claude` command exists.
2. Config file exists and is valid JSON.
3. OS keyring is available.
4. Each vendor has a valid model.
5. Each non-official vendor has a base URL.
6. Each vendor has a valid auth_env.
7. Claude settings files are valid JSON if they exist.
8. Active vendor key exists in secret store.
```

Example output:

```text
Claude API Key Manager Doctor

Claude command: OK
Config file: OK
Secret store: OK
Vendors: 3
  deepseek: key exists, base URL set
  kimi: key exists, base URL set
  official: key exists

Result: OK
```

---

## 15. `claudeapikey test`

Optional but useful:

```bash
claudeapikey test deepseek
```

Checks:

```text
1. Base URL is reachable.
2. Authentication works.
3. `/v1/messages` works or responds in a compatible way.
4. `/v1/messages/count_tokens` works or responds in a compatible way.
5. Optional `/v1/models` works if model discovery is enabled.
```

Important: some providers may be OpenAI-compatible but not Claude Code-compatible. Claude Code gateway compatibility requires an API format Claude Code understands.

---

## 16. Reset commands

### Reset local project settings

```bash
claudeapikey reset --local
```

Removes the managed `claudeapikey` fields from:

```text
./.claude/settings.local.json
```

### Reset global settings

```bash
claudeapikey reset --global
```

Removes the managed `claudeapikey` fields from:

```text
~/.claude/settings.json
```

Do not delete unrelated user settings.

---

## 17. File modification safety

Before modifying Claude Code settings, create a backup.

Example:

```text
~/.claude/settings.json.claudeapikey-backup-20260606-153000
./.claude/settings.local.json.claudeapikey-backup-20260606-153000
```

When writing settings, preserve unrelated fields.

Example existing file:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)"
    ]
  }
}
```

After applying vendor:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)"
    ]
  },
  "model": "deepseek-v4-pro",
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_MODEL": "deepseek-v4-pro",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
  },
  "apiKeyHelper": "claudeapikey key get deepseek --raw"
}
```

---

## 18. Security rules

Minimum security rules:

```text
1. Never print full API keys unless `--raw` is explicitly used.
2. `--raw` should only be used for automation, env generation, or apiKeyHelper.
3. Never write raw API keys to Claude settings by default.
4. Never write raw API keys to shell rc files by default.
5. Never store raw API keys in config.json.
6. Mask keys in normal output.
7. Do not log key values.
8. Do not expose keys through web UI in v1.
9. If a future web UI is added, bind only to 127.0.0.1.
10. Always backup Claude settings before editing them.
```

Masked key display:

```text
sk-...abcd
```

---

## 19. Recommended tech stack

Use Python.

```text
Typer        CLI framework
Pydantic     profile validation
keyring      OS secret storage
rich         terminal output
platformdirs config path handling
requests     optional diagnostics/testing
```

Optional later:

```text
FastAPI      local web UI
Uvicorn      local web server
```

For v1, skip the web UI.

---

## 20. Project structure

```text
claudeapikey/
├── pyproject.toml
├── README.md
├── claudeapikey/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── config_store.py
│   ├── secret_store.py
│   ├── env_builder.py
│   ├── runner.py
│   ├── claude_settings.py
│   └── doctor.py
└── tests/
    ├── test_config_store.py
    ├── test_env_builder.py
    ├── test_claude_settings.py
    └── test_secret_store.py
```

---

## 21. Python package config

`pyproject.toml` should expose:

```toml
[project.scripts]
claudeapikey = "claudeapikey.main:app"
```

Install locally:

```bash
pip install -e .
```

Recommended install later:

```bash
pipx install .
```

---

## 22. Implementation phases

### Phase 1 — CLI MVP

Build:

```text
claudeapikey install
claudeapikey add
claudeapikey list
claudeapikey show
claudeapikey remove
claudeapikey key set
claudeapikey key get --raw
claudeapikey key copy
claudeapikey env
claudeapikey run
claudeapikey doctor
```

Done when this works:

```bash
claudeapikey add deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --auth-env ANTHROPIC_API_KEY \
  --model deepseek-v4-pro

claudeapikey key set deepseek
claudeapikey run deepseek
```

---

### Phase 2 — Claude settings integration

Build:

```text
claudeapikey use <vendor> --local
claudeapikey use <vendor> --global
claudeapikey reset --local
claudeapikey reset --global
```

Done when:

```bash
claudeapikey use deepseek --local
claude
```

uses the configured project-local vendor without placing the raw API key in `.claude/settings.local.json`.

---

### Phase 3 — Diagnostics

Build:

```text
claudeapikey test <vendor>
```

Done when it can detect common issues:

```text
wrong base URL
missing key
wrong auth_env
gateway not Claude-compatible
settings JSON broken
claude command missing
```

---

### Phase 4 — Optional web UI

Only build this later if needed.

Command:

```bash
claudeapikey serve
```

Rules:

```text
1. Bind only to 127.0.0.1.
2. Never display full keys.
3. Allow add/edit/delete vendor.
4. Allow setting keys.
5. Allow copying masked key info only.
6. Allow running diagnostics.
```

---

## 23. Example README quick start

```bash
# Install
pipx install .

# Initialize
claudeapikey install

# Add DeepSeek
claudeapikey add deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --auth-env ANTHROPIC_API_KEY \
  --model deepseek-v4-pro

# Save API key
claudeapikey key set deepseek

# Run Claude Code with DeepSeek
claudeapikey run deepseek
```

Switch to Kimi:

```bash
claudeapikey add kimi \
  --base-url https://your-kimi-gateway.example.com \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --model kimi-k2

claudeapikey key set kimi
claudeapikey run kimi
```

Switch back to official Anthropic:

```bash
claudeapikey add official \
  --official \
  --auth-env ANTHROPIC_API_KEY \
  --model sonnet

claudeapikey key set official
claudeapikey run official
```

---

## 24. Build prompt for Codex or Claude Code

```text
Build a Python CLI tool called `claudeapikey`.

Purpose:
`claudeapikey` is a Claude Code vendor switcher. It lets me add different Claude Code-compatible vendors such as official Anthropic, DeepSeek Anthropic-compatible endpoint, Kimi through a gateway, and outsource providers. It stores vendor profiles and API keys, then launches Claude Code with the correct environment using one command.

Do not create a separate `ccv` command. The only public command should be `claudeapikey`.

Required commands:
- claudeapikey install
- claudeapikey add <vendor>
- claudeapikey edit <vendor>
- claudeapikey list
- claudeapikey show <vendor>
- claudeapikey remove <vendor>
- claudeapikey key set <vendor>
- claudeapikey key get <vendor> --raw
- claudeapikey key delete <vendor>
- claudeapikey key copy <vendor>
- claudeapikey env <vendor>
- claudeapikey run <vendor>
- claudeapikey use <vendor> --local
- claudeapikey use <vendor> --global
- claudeapikey reset --local
- claudeapikey reset --global
- claudeapikey current
- claudeapikey doctor
- claudeapikey test <vendor>
- claudeapikey uninstall

Use Python with:
- Typer
- Pydantic
- keyring
- rich
- platformdirs
- requests

Config:
Store non-secret profile config in the platformdirs user config directory, equivalent to:
~/.config/claudeapikey/config.json

Secret storage:
Use OS keyring. Do not store raw API keys in config.json, .bashrc, .zshrc, .env, ~/.claude/settings.json, or ./.claude/settings.local.json.

Profile schema:
{
  "base_url": "https://provider.example.com",
  "auth_env": "ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN",
  "model": "provider-model-name",
  "official": false,
  "extra_env": {}
}

Behavior:
`claudeapikey run deepseek` should:
1. Load the deepseek vendor profile.
2. Fetch the key from OS keyring.
3. Build env vars:
   - ANTHROPIC_BASE_URL if base_url exists
   - either ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN
   - ANTHROPIC_MODEL
   - any extra_env values
4. Execute `claude --model <model>` with that environment.

`claudeapikey env deepseek` should print shell export lines.

`claudeapikey use deepseek --local` should update ./.claude/settings.local.json using apiKeyHelper instead of raw API keys.

`claudeapikey use official --global` should update ~/.claude/settings.json using apiKeyHelper instead of raw API keys.

Safety:
- Never print full keys except with `key get --raw`.
- `key get --raw` should print only the key and nothing else.
- Create backups before editing Claude settings files.
- Preserve unrelated fields in Claude settings files.
- Validate JSON before writing.
- Provide useful errors when a vendor is missing, key is missing, or `claude` is not installed.

Tests:
Add unit tests for:
- config load/save
- profile validation
- env building
- Claude settings patching
- keyring abstraction with fake backend
- command behavior using Typer CliRunner

Deliver:
- pyproject.toml
- source code
- README.md
- tests
```

---

## 25. Final recommended daily usage

The final user experience should be:

```bash
claudeapikey run deepseek
```

or:

```bash
claudeapikey run kimi
```

or:

```bash
claudeapikey run official
```

That is the whole point of the tool.
