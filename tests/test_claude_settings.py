"""Tests for claude_settings module."""

import json
from pathlib import Path

import pytest

from claudeapikey.claude_settings import (
    LOCAL_SETTINGS,
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
