"""Tests for env_builder module."""

from pathlib import Path

import pytest

from claudeapikey.config_store import save_config
from claudeapikey.env_builder import build_env, build_env_exports
from claudeapikey.models import Config, VendorProfile
from claudeapikey.secret_store import set_key


def test_build_env_gateway(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test-env",
    )
    config = Config(
        vendors={
            "deepseek": VendorProfile(
                base_url="https://api.deepseek.com/anthropic",
                auth_env="ANTHROPIC_API_KEY",
                model="deepseek-v4-pro",
                extra_env={"CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"},
            ),
        },
    )
    save_config(config)
    set_key("deepseek", "sk-test")

    env = build_env("deepseek")
    assert env["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
    assert env["ANTHROPIC_API_KEY"] == "sk-test"
    assert env["ANTHROPIC_MODEL"] == "deepseek-v4-pro"
    assert env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] == "1"


def test_build_env_official(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test-env",
    )
    config = Config(
        vendors={
            "official": VendorProfile(
                auth_env="ANTHROPIC_API_KEY",
                model="sonnet",
                official=True,
            ),
        },
    )
    save_config(config)
    set_key("official", "sk-official")

    env = build_env("official")
    assert "ANTHROPIC_BASE_URL" not in env
    assert env["ANTHROPIC_API_KEY"] == "sk-official"
    assert env["ANTHROPIC_MODEL"] == "sonnet"


def test_build_env_missing_vendor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    save_config(Config())
    with pytest.raises(ValueError, match="not found"):
        build_env("missing")


def test_build_env_missing_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    # Ensure no leftover key from other tests
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test-env-builder",
    )
    config = Config(
        vendors={
            "test": VendorProfile(
                base_url="https://example.com",
                auth_env="ANTHROPIC_API_KEY",
                model="test-model",
            ),
        },
    )
    save_config(config)
    with pytest.raises(RuntimeError, match="not found"):
        build_env("test")


def test_build_env_exports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test-env",
    )
    config = Config(
        vendors={
            "test": VendorProfile(
                base_url="https://example.com",
                auth_env="ANTHROPIC_API_KEY",
                model="test-model",
            ),
        },
    )
    save_config(config)
    set_key("test", "sk-test")

    exports = build_env_exports("test")
    assert "export ANTHROPIC_BASE_URL='https://example.com'" in exports
    assert "export ANTHROPIC_API_KEY='sk-test'" in exports
    assert "export ANTHROPIC_MODEL='test-model'" in exports
