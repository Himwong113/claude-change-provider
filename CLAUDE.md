# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`claudeapikey` is a CLI tool for switching Claude Code between API vendors (official Anthropic, DeepSeek, Kimi, etc.). It stores API keys in the OS keyring and non-secret vendor profiles in a JSON config file. It also provides a FastAPI web dashboard and can write vendor configs into Claude Code's `settings.json` via an `apiKeyHelper` shell command.

## Development Commands

Setup (creates `claudeapikey`, installs package, runs `claudeapikey install`):
```bash
./init.sh
source .claudeapikey/bin/activate
```

Run tests:
```bash
pytest
pytest --cov=claudeapikey
```

Run a single test file or test:
```bash
pytest tests/test_cli.py
pytest tests/test_cli.py::test_add_and_list
```

Format / lint (optional tooling):
```bash
black claudeapikey/ tests/
ruff check claudeapikey/ tests/
```

Run the CLI in development:
```bash
claudeapikey --help
```

Run the web dashboard:
```bash
claudeapikey serve
# or directly:
uvicorn claudeapikey.web_server:app --host 127.0.0.1 --port 8787
```

## Architecture

### Module Responsibilities

- **`claudeapikey/main.py`** — Typer CLI entry point. Defines all commands (`add`, `edit`, `list`, `remove`, `key`, `run`, `env`, `use`, `reset`, `serve`, `doctor`, `service`, `install`, `uninstall`). Sub-apps: `key_app` and `service_app`.
- **`claudeapikey/models.py`** — Pydantic v2 models. `VendorProfile` validates that non-official vendors have a `base_url`. `Config` holds `active_vendor` and a map of vendor names to profiles.
- **`claudeapikey/config_store.py`** — Reads/writes `~/.config/claudeapikey/config.json` (via `platformdirs`). File permissions are set to `0o600`.
- **`claudeapikey/secret_store.py`** — Abstraction over the `keyring` library. Service name is `"claudeapikey"`, account is `"vendor:<name>"`. Keys are masked with `mask_key()` for display.
- **`claudeapikey/env_builder.py`** — Builds environment variables for a vendor (`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, plus `extra_env`). Used by `run` and `env` commands.
- **`claudeapikey/runner.py`** — Finds `claude` in PATH and uses `os.execvpe` to replace the current process with `claude --model <model>`.
- **`claudeapikey/claude_settings.py`** — Reads/writes Claude Code settings files (`~/.claude/settings.json` and `./.claude/settings.local.json`). Backs up files before mutating. Managed keys: `model`, `env`, `apiKeyHelper`. Resetting removes only those keys.
- **`claudeapikey/doctor.py`** — Diagnostic checks for `claude` binary, config JSON validity, keyring availability, vendor profile validity, and settings file validity.
- **`claudeapikey/systemd_service.py`** — Generates a systemd user service unit that runs `uvicorn claudeapikey.web_server:app`. Unit file lives at `~/.config/systemd/user/claudeapikey.service`.
- **`claudeapikey/web_server.py`** — FastAPI app serving a Jinja2 dashboard at `/` and a REST API under `/api/vendors`, `/api/doctor`. Full API keys are never returned; only masked versions.
- **`claudeapikey/templates/index.html`** — Single Jinja2 template with inline CSS and JS for the dashboard.

### Security Model

- API keys are **never** written to config JSON, `.env`, shell rc files, or Claude settings files.
- `apiKeyHelper` in settings files references `claudeapikey key get <vendor> --raw` so Claude Code fetches the key on demand from the OS keyring.
- Dashboard binds only to `127.0.0.1` by default.
- Keys are masked in UI and CLI output unless `--raw` is passed.

### Testing Patterns

Tests use `pytest` and monkeypatch paths/keyring to avoid touching the real filesystem and OS keyring:

```python
@pytest.fixture(autouse=True)
def isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("claudeapikey.config_store.CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr("claudeapikey.config_store.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("claudeapikey.secret_store.SERVICE_NAME", "claudeapikey-test")
```

CLI tests use `typer.testing.CliRunner` against `claudeapikey.main.app`. Web tests use `fastapi.testclient.TestClient` against `claudeapikey.web_server.app`.

## Build & Packaging

- Build backend: `hatchling`
- Entry point: `claudeapikey = "claudeapikey.main:app"`
- Dev dependencies in `[project.optional-dependencies]` under `dev`: `pytest`, `pytest-cov`, `httpx`
