# Setup Failure Prevention

This note records what was changed during the `localhost:8787` multi-model proxy fix and how to avoid the same setup failure next time.

## What Changed

- Project-local Claude settings now use one stable endpoint: `http://localhost:8787`.
- `ANTHROPIC_API_KEY` in Claude settings is only the dummy value `local-proxy`; real vendor keys stay in the OS keyring.
- Proxy tier aliases were cleaned so Claude can route models through one setting:
  - `default`: `glm-5.2`
  - `haiku`: `deepseek-v4-pro`
  - `sonnet`: `kimi-k2.7-code`
  - `opus`: `glm-5.2`
  - `subagent`: `kimi-k2.7-code`
- The accidental DeepSeek model value `deepseek-v4-pro[1m]` was corrected to `deepseek-v4-pro`.
- The proxy now accepts provider URLs saved as a base URL, a `/v1` URL, or a full `/v1/messages` URL.
- The proxy now respects each vendor's saved auth mode:
  - `ANTHROPIC_API_KEY` vendors receive an upstream `x-api-key` header.
  - `ANTHROPIC_AUTH_TOKEN` vendors receive an upstream `Authorization: Bearer ...` header.
- The settings writer no longer writes the internal `default` proxy tier into Claude's environment as `env.default`.

## Why Setup Failed

The setup was mostly present, but a few small mismatches made it fragile:

- Claude needed a single local endpoint, but the running proxy and generated settings had to agree on `localhost:8787`.
- One model route had terminal formatting text copied into it: `deepseek-v4-pro[1m]`.
- Some provider config values had copied shell syntax such as `export ...` in `extra_env`; config keys should be raw names like `ANTHROPIC_MODEL`, not shell commands.
- The proxy previously sent all upstream keys as bearer auth, even for vendors configured as `ANTHROPIC_API_KEY`.
- If the server on port `8787` is stale or not running, Claude can have correct settings but still fail to send requests.

## Good Setup Checklist

Run the installer from this checkout. `./init.sh` is the all-in-one setup and recovery entry point.

```bash
./init.sh
```

The installer now handles the normal recovery chores in one pass:

- installs or refreshes the editable package
- checks that this checkout is the package being imported
- offers to set any missing vendor API keys
- repairs non-secret config mistakes such as copied `export ` prefixes and terminal color fragments
- enables/applies local proxy settings when requested
- checks whether `127.0.0.1:8787` is reachable
- offers to start the proxy/dashboard in the background if it is enabled but not running

For multi-model mode, use these commands:

```bash
claudeapikey proxy enable --local
claudeapikey serve --kill
claudeapikey proxy status
claude
```

Check health before launching Claude if something feels off:

```bash
curl http://127.0.0.1:8787/v1/health
```

Expected response:

```json
{"status":"ok","proxy":true}
```

Check routes:

```bash
claudeapikey proxy status
```

Make sure every route uses the exact model string expected by the provider. Do not include terminal color fragments like `[1m`, `[0m`, or copied shell text.

## Vendor Config Rules

Use clean model names:

```bash
claudeapikey edit deepseek --model deepseek-v4-pro
```

Use clean extra environment keys. Good:

```text
ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-pro
CLAUDE_CODE_SUBAGENT_MODEL=kimi-k2.7-code
```

Bad:

```text
export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-pro
```

Store secrets only through keyring:

```bash
claudeapikey key set deepseek
claudeapikey key set kimi
claudeapikey key set glm
```

## Recovery Commands

If the proxy port is stuck or the server is stale:

```bash
claudeapikey serve --kill
```

If Claude settings drift from the saved proxy config:

```bash
claudeapikey proxy apply --local
```

If a vendor route is wrong:

```bash
claudeapikey edit <vendor> --model <clean-model>
claudeapikey proxy status
```

If you need a full diagnostic pass:

```bash
claudeapikey doctor
```

## Validation Used For This Fix

The code changes were validated with:

```bash
pytest
pytest tests/test_proxy.py
pytest tests/test_claude_settings.py
curl http://127.0.0.1:8787/v1/health
curl http://127.0.0.1:8787/api/proxy/status
```