"""Tests for config_store module."""

import json
from pathlib import Path

import pytest

from claudeapikey.config_store import load_config, save_config
from claudeapikey.models import Config, VendorProfile


def test_load_config_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    config = load_config()
    assert config.active_vendor is None
    assert config.vendors == {}


def test_save_and_load_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    config = Config(
        active_vendor="deepseek",
        vendors={
            "deepseek": VendorProfile(
                base_url="https://api.deepseek.com/anthropic",
                auth_env="ANTHROPIC_API_KEY",
                model="deepseek-v4-pro",
            ),
        },
    )
    save_config(config)

    loaded = load_config()
    assert loaded.active_vendor == "deepseek"
    assert "deepseek" in loaded.vendors
    assert loaded.vendors["deepseek"].model == "deepseek-v4-pro"


def test_config_file_permissions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    save_config(Config())
    config_file = tmp_path / "config.json"
    mode = config_file.stat().st_mode
    assert mode & 0o777 == 0o600
