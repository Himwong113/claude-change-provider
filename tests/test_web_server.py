"""Tests for FastAPI web server."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claudeapikey.web_server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_FILE",
        tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "claudeapikey.config_store.CONFIG_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "claudeapikey.secret_store.SERVICE_NAME",
        "claudeapikey-test-web",
    )


def test_index_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "claudeapikey" in response.text


def test_api_list_vendors_empty() -> None:
    response = client.get("/api/vendors")
    assert response.status_code == 200
    data = response.json()
    assert data["vendors"] == []


def test_api_add_vendor() -> None:
    response = client.post(
        "/api/vendors/test",
        data={
            "base_url": "https://example.com",
            "auth_env": "ANTHROPIC_API_KEY",
            "model": "test-model",
            "official": "false",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_add_vendor_duplicate() -> None:
    client.post(
        "/api/vendors/dup",
        data={"base_url": "https://dup.com", "auth_env": "ANTHROPIC_API_KEY", "model": "m", "official": "false"},
    )
    response = client.post(
        "/api/vendors/dup",
        data={"base_url": "https://dup.com", "auth_env": "ANTHROPIC_API_KEY", "model": "m", "official": "false"},
    )
    assert response.status_code == 409


def test_api_edit_vendor() -> None:
    client.post(
        "/api/vendors/editme",
        data={"base_url": "https://editme.com", "auth_env": "ANTHROPIC_API_KEY", "model": "old", "official": "false"},
    )
    response = client.put(
        "/api/vendors/editme",
        data={"model": "new"},
    )
    assert response.status_code == 200


def test_api_remove_vendor() -> None:
    client.post(
        "/api/vendors/rm",
        data={"base_url": "https://rm.com", "auth_env": "ANTHROPIC_API_KEY", "model": "m", "official": "false"},
    )
    response = client.delete("/api/vendors/rm")
    assert response.status_code == 200


def test_api_key_management() -> None:
    client.post(
        "/api/vendors/keytest",
        data={"base_url": "https://keytest.com", "auth_env": "ANTHROPIC_API_KEY", "model": "m", "official": "false"},
    )
    response = client.post(
        "/api/vendors/keytest/key",
        data={"key": "sk-secret"},
    )
    assert response.status_code == 200

    response = client.get("/api/vendors")
    data = response.json()
    vendor = next(v for v in data["vendors"] if v["name"] == "keytest")
    assert vendor["key_set"] is True

    response = client.delete("/api/vendors/keytest/key")
    assert response.status_code == 200


def test_api_env_missing_key() -> None:
    client.post(
        "/api/vendors/envtest",
        data={"base_url": "https://envtest.com", "auth_env": "ANTHROPIC_API_KEY", "model": "m", "official": "false"},
    )
    response = client.get("/api/vendors/envtest/env")
    assert response.status_code == 400


def test_api_doctor() -> None:
    response = client.get("/api/doctor")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "ok" in data


def test_proxy_status() -> None:
    response = client.get("/api/proxy/status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["url"] == "http://localhost:8787"
    assert data["routes"] == []
    assert data["tiers"] == {}


def test_proxy_enable_disable() -> None:
    response = client.post("/api/proxy/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True

    response = client.get("/api/proxy/status")
    assert response.json()["enabled"] is True

    response = client.post("/api/proxy/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_proxy_tiers() -> None:
    response = client.put("/api/proxy/tiers", data={"tiers": "haiku=kimi\nsonnet=glm"})
    assert response.status_code == 200
    assert response.json()["tiers"] == {"haiku": "kimi", "sonnet": "glm"}

    response = client.get("/api/proxy/status")
    assert response.json()["tiers"] == {"haiku": "kimi", "sonnet": "glm"}


def test_proxy_health() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["proxy"] is True


def test_proxy_messages_disabled_by_default() -> None:
    response = client.post("/v1/messages", json={"model": "m1"})
    assert response.status_code == 503
