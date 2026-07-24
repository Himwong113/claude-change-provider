# Upgrading `claudeapikey` to Kimi K2.7 Code

This document explains how to add a working Kimi K2.7 Code vendor alongside (or instead of) the K3 vendor.

## Correct Kimi K2.7 Code configuration

| Setting | Value |
|---|---|
| Vendor name | `kimi-k27` |
| Base URL | `https://api.kimi.com/coding/` |
| Auth env | `ANTHROPIC_AUTH_TOKEN` |
| Model | `kimi-for-coding` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `kimi-for-coding` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `kimi-for-coding` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `kimi-for-coding` |
| `ANTHROPIC_DEFAULT_FABLE_MODEL` | `kimi-for-coding` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `kimi-for-coding` |
| `ENABLE_TOOL_SEARCH` | `false` |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | `262144` (256K context) |
| `CLAUDE_CODE_EFFORT_LEVEL` | `max` |

For the **high-speed** variant, use `kimi-for-coding-highspeed` instead of `kimi-for-coding`.

## Quick upgrade

Run the helper script from the repo root:

```bash
./upgrade-to-k27.sh
```

It will:

1. Back up your `claudeapikey` config.
2. Create or update the `kimi-k27` vendor with the values above.
3. Copy the existing `kimi` API key to `kimi-k27` if one is stored.
4. Update proxy tier aliases to `kimi-for-coding` if proxy mode is enabled.
5. Apply the settings to your local Claude Code settings file.

If no API key is stored, the script will prompt for one.

## Manual upgrade

```bash
# Create/update the K2.7 vendor
claudeapikey add kimi-k27 \
  --base-url https://api.kimi.com/coding/ \
  --auth-env ANTHROPIC_AUTH_TOKEN \
  --model kimi-for-coding \
  --extra-env ANTHROPIC_DEFAULT_OPUS_MODEL=kimi-for-coding \
  --extra-env ANTHROPIC_DEFAULT_SONNET_MODEL=kimi-for-coding \
  --extra-env ANTHROPIC_DEFAULT_HAIKU_MODEL=kimi-for-coding \
  --extra-env ANTHROPIC_DEFAULT_FABLE_MODEL=kimi-for-coding \
  --extra-env CLAUDE_CODE_SUBAGENT_MODEL=kimi-for-coding \
  --extra-env ENABLE_TOOL_SEARCH=false \
  --extra-env CLAUDE_CODE_AUTO_COMPACT_WINDOW=262144 \
  --extra-env CLAUDE_CODE_EFFORT_LEVEL=max

# Set the API key
claudeapikey key set kimi-k27
```

If you use **proxy mode**, route tiers to K2.7:

```bash
python3 - <<'PY'
from claudeapikey.config_store import load_config, save_config
config = load_config()
for tier in config.proxy_tiers:
    config.proxy_tiers[tier] = "kimi-for-coding"
save_config(config)
PY

claudeapikey proxy apply --local
```

If you do **not** use proxy mode:

```bash
claudeapikey use kimi-k27 --local
```

## Running Claude Code

### Proxy mode

```bash
# Terminal 1
claudeapikey serve

# Terminal 2
claude
```

### Direct mode

```bash
claudeapikey run kimi-k27
```

## Important notes

- Avoid copying styled terminal text into config values — ANSI codes like `[1m` will break model lookups.
- In proxy mode, extra env vars (`ENABLE_TOOL_SEARCH`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_EFFORT_LEVEL`) are not written to `.claude/settings.local.json` automatically. Export them in the shell that launches `claude`, or add them to the `env` section of your settings file.
