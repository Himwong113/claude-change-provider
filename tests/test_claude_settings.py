"""Tests for claude_settings module."""

import json
from pathlib import Path

import pytest

from claudeapikey.claude_settings import (
    LOCAL_SETTINGS,
    apply_proxy_settings,
    apply_vendor,
    reset_settings,
)
from claudeapikey.config_store import save_config
from claudeapikey.models import Config, VendorProfile


def test_apply_vendor_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.claude_settings.LOCAL_SETTINGS",
        tmp_path / ".claude" / "settings.local.json",
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

    apply_vendor("deepseek", local=True)

    settings_path = tmp_path / ".claude" / "settings.local.json"
    with open(settings_path) as f:
        data = json.load(f)

    assert data["model"] == "deepseek-v4-pro"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
    assert data["env"]["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] == "1"
    assert data["apiKeyHelper"] == "claudeapikey key get deepseek --raw"


def test_reset_settings_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.claude_settings.LOCAL_SETTINGS",
        tmp_path / ".claude" / "settings.local.json",
    )

    settings_path = tmp_path / ".claude" / "settings.local.json"
    settings_path.parent.mkdir(parents=True)
    with open(settings_path, "w") as f:
        json.dump({"model": "x", "env": {}, "apiKeyHelper": "h", "permissions": {}}, f)

    reset_settings(local=True)

    with open(settings_path) as f:
        data = json.load(f)

    assert "model" not in data
    assert "env" not in data
    assert "apiKeyHelper" not in data
    assert data["permissions"] == {}


def test_preserve_unrelated_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.claude_settings.LOCAL_SETTINGS",
        tmp_path / ".claude" / "settings.local.json",
    )

    config = Config(
        vendors={
            "deepseek": VendorProfile(
                base_url="https://api.deepseek.com/anthropic",
                auth_env="ANTHROPIC_API_KEY",
                model="deepseek-v4-pro",
            ),
        },
    )
    save_config(config)

    settings_path = tmp_path / ".claude" / "settings.local.json"
    settings_path.parent.mkdir(parents=True)
    with open(settings_path, "w") as f:
        json.dump({"permissions": {"deny": ["Read(./.env)"]}}, f)

    apply_vendor("deepseek", local=True)

    with open(settings_path) as f:
        data = json.load(f)

    assert data["permissions"]["deny"] == ["Read(./.env)"]
    assert data["model"] == "deepseek-v4-pro"


def test_apply_proxy_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.claude_settings.LOCAL_SETTINGS",
        tmp_path / ".claude" / "settings.local.json",
    )

    config = Config(
        proxy_enabled=True,
        proxy_port=8787,
        proxy_tiers={"haiku": "kimi-k2.7-code", "sonnet": "glm-5.2"},
        vendors={
            "kimi": VendorProfile(base_url="https://api.kimi.com", model="kimi-k2.7-code"),
            "glm": VendorProfile(base_url="https://api.glm.com", model="glm-5.2"),
        },
    )
    save_config(config)

    apply_proxy_settings(port=8787, local=True)

    settings_path = tmp_path / ".claude" / "settings.local.json"
    with open(settings_path) as f:
        data = json.load(f)

    assert data["env"]["ANTHROPIC_BASE_URL"] == "http://localhost:8787"
    assert data["env"]["ANTHROPIC_API_KEY"] == "local-proxy"
    assert data["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "kimi-k2.7-code"
    assert data["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-5.2"
    assert "apiKeyHelper" not in data


def test_apply_vendor_uses_proxy_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.claude_settings.LOCAL_SETTINGS",
        tmp_path / ".claude" / "settings.local.json",
    )

    config = Config(
        proxy_enabled=True,
        vendors={
            "kimi": VendorProfile(base_url="https://api.kimi.com", model="kimi-k2.7-code"),
        },
    )
    save_config(config)

    apply_vendor("kimi", local=True)

    settings_path = tmp_path / ".claude" / "settings.local.json"
    with open(settings_path) as f:
        data = json.load(f)

    assert data["env"]["ANTHROPIC_BASE_URL"] == "http://localhost:8787"
    assert data["model"] == "kimi-k2.7-code"
    assert "apiKeyHelper" not in data


def test_apply_proxy_settings_uses_default_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.claude_settings.LOCAL_SETTINGS",
        tmp_path / ".claude" / "settings.local.json",
    )

    config = Config(
        proxy_enabled=True,
        proxy_tiers={"default": "glm-5.2"},
        vendors={
            "kimi": VendorProfile(base_url="https://api.kimi.com", model="kimi-k2.7-code"),
            "glm": VendorProfile(base_url="https://api.glm.com", model="glm-5.2"),
        },
    )
    save_config(config)

    apply_proxy_settings(port=8787, local=True)

    settings_path = tmp_path / ".claude" / "settings.local.json"
    with open(settings_path) as f:
        data = json.load(f)

    assert data["model"] == "glm-5.2"
    assert data["env"]["ANTHROPIC_MODEL"] == "glm-5.2"
    assert "default" not in data["env"]
