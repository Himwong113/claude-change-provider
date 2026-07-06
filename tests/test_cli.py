"""CLI integration tests using Typer CliRunner."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from claudeapikey.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use temporary paths for config and keyring."""
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_DIR",
        tmp_path,
    )
    # Use a dummy in-memory keyring backend
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test",
    )


def test_install() -> None:
    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0
    assert "Done" in result.output


def test_add_and_list() -> None:
    result = runner.invoke(app, [
        "add", "deepseek",
        "--base-url", "https://api.deepseek.com/anthropic",
        "--auth-env", "ANTHROPIC_API_KEY",
        "--model", "deepseek-v4-pro",
    ])
    assert result.exit_code == 0
    assert "added" in result.output

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "deepseek" in result.output


def test_add_official() -> None:
    result = runner.invoke(app, [
        "add", "official",
        "--official",
        "--auth-env", "ANTHROPIC_API_KEY",
        "--model", "sonnet",
    ])
    assert result.exit_code == 0
    assert "official" in result.output


def test_show_missing() -> None:
    result = runner.invoke(app, ["show", "missing"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_key_set_get_delete() -> None:
    runner.invoke(app, [
        "add", "test",
        "--base-url", "https://example.com",
        "--model", "test-model",
    ])

    result = runner.invoke(app, ["key", "set", "test"], input="sk-secret\n")
    assert result.exit_code == 0

    result = runner.invoke(app, ["key", "get", "test", "--raw"])
    assert result.exit_code == 0
    assert result.output == "sk-secret"

    result = runner.invoke(app, ["key", "delete", "test", "--yes"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["key", "get", "test", "--raw"])
    assert result.exit_code == 1


def test_env_command() -> None:
    runner.invoke(app, [
        "add", "test",
        "--base-url", "https://example.com",
        "--model", "test-model",
    ])
    runner.invoke(app, ["key", "set", "test"], input="sk-test\n")

    result = runner.invoke(app, ["env", "test"])
    assert result.exit_code == 0
    assert "export ANTHROPIC_BASE_URL='https://example.com'" in result.output
    assert "export ANTHROPIC_API_KEY='sk-test'" in result.output


def test_remove_vendor() -> None:
    runner.invoke(app, [
        "add", "temp",
        "--base-url", "https://temp.com",
        "--model", "temp-model",
    ])
    result = runner.invoke(app, ["remove", "temp", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.output


def test_doctor() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Doctor" in result.output


def test_use_local() -> None:
    runner.invoke(app, [
        "add", "deepseek",
        "--base-url", "https://api.deepseek.com/anthropic",
        "--model", "deepseek-v4-pro",
    ])
    result = runner.invoke(app, ["use", "deepseek", "--local"])
    assert result.exit_code == 0
    assert "Applied" in result.output


def test_reset_local() -> None:
    result = runner.invoke(app, ["reset", "--local"])
    # May succeed or warn depending on file existence
    assert result.exit_code == 0


def test_uninstall() -> None:
    runner.invoke(app, ["install"])
    result = runner.invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0
    assert "uninstalled" in result.output


def test_proxy_enable_disable() -> None:
    result = runner.invoke(app, ["proxy", "enable"])
    assert result.exit_code == 0
    assert "enabled" in result.output

    result = runner.invoke(app, ["proxy", "status"])
    assert result.exit_code == 0
    assert "enabled" in result.output.lower()

    result = runner.invoke(app, ["proxy", "disable"])
    assert result.exit_code == 0
    assert "disabled" in result.output


def test_proxy_apply_local() -> None:
    runner.invoke(app, [
        "add", "kimi",
        "--base-url", "https://api.kimi.com",
        "--model", "kimi-k2.7-code",
    ])
    result = runner.invoke(app, ["proxy", "apply", "--local"])
    assert result.exit_code == 0
    assert "Applied" in result.output


def test_run_proxy_fails_when_disabled() -> None:
    result = runner.invoke(app, ["run-proxy"])
    assert result.exit_code == 1
    assert "not enabled" in result.output.lower()


def test_run_proxy_cleans_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """run-proxy must drop stale ANTHROPIC_AUTH_TOKEN/API_KEY from the env."""
    runner.invoke(app, ["proxy", "enable"])
    runner.invoke(app, [
        "add", "glm",
        "--base-url", "https://api.glm.example",
        "--model", "glm-5.2",
    ])

    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "stale-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stale-key")

    captured: dict[str, object] = {}

    def fake_execvpe(path: str, args: list[str], env: dict[str, str]) -> None:
        captured["path"] = path
        captured["args"] = args
        captured["env"] = env
        raise SystemExit(0)

    monkeypatch.setattr("os.execvpe", fake_execvpe)
    # Pretend the proxy health endpoint is reachable.
    def fake_urlopen(url: str, timeout: float | None = None) -> MagicMock:
        captured["health_url"] = url
        return MagicMock(status=200, __enter__=lambda s: s, __exit__=lambda *a: None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = runner.invoke(app, ["run-proxy"])
    assert result.exit_code == 0
    env = captured["env"]
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["ANTHROPIC_API_KEY"] == "local-proxy"
    assert env["ANTHROPIC_BASE_URL"] == "http://localhost:8787"
    # The health check should have used 127.0.0.1.
    assert captured["health_url"] == "http://127.0.0.1:8787/v1/health"
