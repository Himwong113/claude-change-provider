# Model-Routing Proxy

`claudeapikey` can act as a small local Anthropic-compatible proxy. Claude Code points its API base URL at `http://127.0.0.1:8787`, and the proxy routes each request to the right stored vendor by reading the `model` field from the request body. The proxy injects the vendor's stored API key, so Claude Code only needs a dummy key to start.

This is useful when you want different Claude Code tiers to use different providers:

```text
haiku   → kimi-k2.7-code
sonnet  → glm-5.2
opus    → claude-opus
```

## How it works

1. You add one vendor per model/backend.
2. You enable proxy mode (`claudeapikey proxy enable --local`).
3. `claudeapikey serve` starts the dashboard **and** the proxy on the same port.
4. Claude Code sends requests to `http://localhost:8787/v1/messages`.
5. The proxy reads `model` from the JSON body, looks up the matching vendor, and forwards the request to that vendor's `base_url` with its stored key.

## Setup

### 1. Add vendors

Each vendor's `model` becomes a routing key.

```bash
claudeapikey add kimi \
  --base-url https://api.kimi.com/coding \
  --model kimi-k2.7-code
claudeapikey key set kimi

claudeapikey add glm \
  --base-url https://api.glm.example \
  --model glm-5.2
claudeapikey key set glm

claudeapikey add official \
  --official \
  --model claude-opus
claudeapikey key set official
```

### 2. Enable the proxy

```bash
# Apply to the current project only
claudeapikey proxy enable --local

# Or apply globally
claudeapikey proxy enable --global
```

This writes Claude Code settings with:

```json
{
  "model": "kimi-k2.7-code",
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:8787",
    "ANTHROPIC_API_KEY": "local-proxy"
  }
}
```

`ANTHROPIC_API_KEY=local-proxy` is a placeholder — the proxy replaces it with the real vendor key before forwarding.

### 3. Map tiers to models

Use the dashboard or the `/api/proxy/tiers` endpoint.

```bash
claudeapikey serve
```

Open `http://127.0.0.1:8787`, go to **Proxy Mode**, and use the dropdowns:

| Tier | Model |
|------|-------|
| Default | `kimi-k2.7-code` |
| haiku | `kimi-k2.7-code` |
| sonnet | `glm-5.2` |
| opus | `claude-opus` |
| subagent | `kimi-k2.7-code` |

The dropdowns are populated from the `model` values of your stored vendors. Custom tier names can be added in the **Custom tiers** textarea (one `KEY=VALUE` per line).

### 4. Start Claude Code

```bash
claude
```

Claude Code will now send API requests to `http://localhost:8787`. The proxy routes by model and injects the correct key.

## CLI commands

| Command | Description |
|---------|-------------|
| `claudeapikey proxy enable [--port 8787] --local` | Enable proxy and apply to local settings |
| `claudeapikey proxy enable [--port 8787] --global` | Enable proxy and apply to global settings |
| `claudeapikey proxy disable` | Disable proxy mode |
| `claudeapikey proxy status` | Show proxy status and model routes |
| `claudeapikey proxy apply --local` | Write proxy settings without toggling the enable flag |

## Dashboard UI

The dashboard's **Proxy Mode** card shows:

- Enable/disable toggle
- Proxy URL
- Tier alias dropdowns (default, haiku, sonnet, opus, subagent)
- Custom tier textarea
- Route preview table (model → vendor)

## Routing rules

- The proxy matches the incoming `model` field against each vendor's `model` value.
- The first match wins.
- Official vendors route to `https://api.anthropic.com/v1/messages`.
- Custom vendors route to `<base_url>/v1/messages`.
- If no vendor matches, the proxy returns `404` with a list of available models.

## Security notes

- The proxy binds to the same loopback interface as the dashboard (`127.0.0.1` by default).
- The proxy never logs request/response bodies or headers.
- Vendor keys stay in the OS keyring; the proxy reads them at request time.
- The `/v1/*` endpoints are exempt from CSRF checks because Claude Code calls them directly, not from a browser.
