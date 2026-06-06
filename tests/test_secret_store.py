"""Tests for secret_store module."""

import pytest

from claudeapikey.secret_store import (
    SERVICE_NAME,
    delete_key,
    get_key,
    key_exists,
    mask_key,
    set_key,
)


@pytest.fixture(autouse=True)
def isolate_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test-secret",
    )


def test_set_get_delete_key() -> None:
    set_key("test-vendor", "secret123")
    assert get_key("test-vendor") == "secret123"
    assert key_exists("test-vendor") is True

    delete_key("test-vendor")
    assert get_key("test-vendor") is None
    assert key_exists("test-vendor") is False


def test_mask_key() -> None:
    assert mask_key("sk-abc123def456") == "sk-...f456"
    assert mask_key("short") == "*****"
    assert mask_key("exactlyten") == "**********"


def test_delete_nonexistent() -> None:
    # Should not raise
    delete_key("nonexistent-vendor")
