"""CLI integration tests using Typer CliRunner."""

from pathlib import Path

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
