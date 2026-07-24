# Upgrading `claudeapikey` to Kimi K3

This document explains why Kimi K3 was failing and the exact configuration needed to make it work.

## What was broken

The stored vendor/profile had three problems:

1. **ANSI escape contamination** — the model string was saved as `kimi-k3[1m]` instead of `k3`. The `[1m]` is an ANSI bold marker that got copied from terminal output. Kimi rejects it as an unknown model.
2. **Wrong model ID for the Kimi Code endpoint** — the Kimi Code Anthropic-compatible endpoint (`api.kimi.com/coding`) expects `k3`, not `kimi-k3`. (`kimi-k3` is the ID for the general Moonshot API.)
3. **Base URL shape** — `https://api.kimi.com/coding/v1` can cause Claude Code’s Anthropic SDK to build a double `/v1/v1/messages` path (404). The correct Anthropic base URL is `https://api.kimi.com/coding/` (trailing slash).

## Correct Kimi K3 configuration

| Setting | Value |
|---|---|
| Vendor name | `kimi` |
| Base URL | `https://api.kimi.com/coding/` |
| Auth env | `ANTHROPIC_AUTH_TOKEN` |
| Model | `k3` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `k3` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `k3` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `k3` |
| `ANTHROPIC_DEFAULT_FABLE_MODEL` | `k3` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `k3` |
| `ENABLE_TOOL_SEARCH` | `false` |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | `1048576` (1M context) |
| `CLAUDE_CODE_EFFORT_LEVEL` | `max` |

## Quick upgrade

Run the helper script from the repo root:

```bash
./upgrade-to-k3.sh
```

It will:

1. Back up your `claudeapikey` config.
2. Create or update the `kimi` vendor with the values above.
3. Update proxy tier aliases to `k3` if proxy mode is enabled.
4. Apply the settings to your local Claude Code settings file.

If you do not have a Kimi API key stored yet, the script will prompt for one.

## Manual upgrade

If you prefer to do it by hand:

```bash
# Update the vendor
claudeapikey edit kimi \
  --model k3 \
  --base-url https://api.kimi.com/coding/ \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --extra-env ANTHROPIC_DEFAULT_OPUS_MODEL=k3 \
  --extra-env ANTHROPIC_DEFAULT_SONNET_MODEL=k3 \
  --extra-env ANTHROPIC_DEFAULT_HAIKU_MODEL=k3 \
  --extra-env ANTHROPIC_DEFAULT_FABLE_MODEL=k3 \
  --extra-env CLAUDE_CODE_SUBAGENT_MODEL=k3 \
  --extra-env ENABLE_TOOL_SEARCH=false \
  --extra-env CLAUDE_CODE_AUTO_COMPACT_WINDOW=1048576 \
  --extra-env CLAUDE_CODE_EFFORT_LEVEL=max

# Set the API key if you have not already
claudeapikey key set kimi
```

If you use **proxy mode**, also update the tier aliases:

```bash
# Start the dashboard/proxy and change the tiers in the UI, or use this Python snippet:
python3 - <<'PY'
from claudeapikey.config_store import load_config, save_config
config = load_config()
for tier in config.proxy_tiers:
    config.proxy_tiers[tier] = "k3"
save_config(config)
PY

claudeapikey proxy apply --local
```

If you do **not** use proxy mode:

```bash
claudeapikey use kimi --local
```

## Running Claude Code

### Proxy mode

Proxy mode is enabled when `ANTHROPIC_BASE_URL` points to `http://localhost:8787`.

```bash
# Terminal 1
claudeapikey serve

# Terminal 2
claude
```

Make sure the proxy is running before starting Claude Code, otherwise every request will fail to connect.

### Direct mode

```bash
claudeapikey run kimi
```

## Important notes

- Do **not** copy values from a `claudeapikey show` table by selecting the styled terminal text — the ANSI bold codes can end up in the stored config. Use `claudeapikey env <vendor>` or type values manually.
- In proxy mode, the extra env vars (`ENABLE_TOOL_SEARCH`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_EFFORT_LEVEL`) are **not** written into `.claude/settings.local.json` automatically. Export them in the shell that launches `claude`, or add them to the `env` section of your settings file.
- If you want Kimi K2.7 Code as well, add a second vendor (e.g. `kimi-k27`) with model `kimi-for-coding`.
