"""Tests for the model-routing proxy."""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from claudeapikey.config_store import save_config
from claudeapikey.models import Config, VendorProfile
from claudeapikey.proxy import (
    build_target_url,
    extract_model,
    forward_messages,
    get_auth_header,
    resolve_vendor,
)
from claudeapikey.secret_store import set_key


@pytest.fixture(autouse=True)
def isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("claudeapikey.config_store.CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr("claudeapikey.config_store.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("claudeapikey.secret_store.SERVICE_NAME", "claudeapikey-test-proxy")

    # In-memory keyring to keep tests isolated and fast.
    memory: dict[tuple[str, str], str] = {}
    monkeypatch.setattr(
        "keyring.set_password",
        lambda service, username, password: memory.update({(service, username): password}),
    )
    monkeypatch.setattr(
        "keyring.get_password",
        lambda service, username: memory.get((service, username)),
    )
    monkeypatch.setattr(
        "keyring.delete_password",
        lambda service, username: memory.pop((service, username), None),
    )


def _request_with_body(body: bytes) -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {"type": "http", "method": "POST", "path": "/v1/messages", "headers": []},
        receive=receive,
    )


def test_extract_model_valid() -> None:
    body = json.dumps({"model": "kimi-k2.7-code"}).encode()
    assert extract_model(body) == "kimi-k2.7-code"


def test_extract_model_missing() -> None:
    body = json.dumps({"messages": []}).encode()
    assert extract_model(body) is None


def test_extract_model_invalid_json() -> None:
    assert extract_model(b"not-json") is None


def test_resolve_vendor_found() -> None:
    profile = VendorProfile(base_url="https://api.example.com", model="m1")
    config = Config(vendors={"v1": profile})
    assert resolve_vendor("m1", config) == ("v1", profile)


def test_resolve_vendor_not_found() -> None:
    config = Config(vendors={"v1": VendorProfile(base_url="https://api.example.com", model="m1")})
    assert resolve_vendor("m2", config) is None


def test_build_target_url_official() -> None:
    vendor = VendorProfile(model="claude", official=True)
    assert build_target_url(vendor) == "https://api.anthropic.com/v1/messages"


def test_build_target_url_custom() -> None:
    vendor = VendorProfile(base_url="https://api.example.com/anthropic", model="m1")
    assert build_target_url(vendor) == "https://api.example.com/anthropic/v1/messages"


def test_get_auth_header() -> None:
    assert get_auth_header("sk-test") == {"Authorization": "Bearer sk-test"}


async def _async_iter(items: list[bytes]) -> AsyncIterator[bytes]:
    for item in items:
        yield item


def test_forward_messages_proxy_disabled() -> None:
    save_config(Config())
    request = _request_with_body(json.dumps({"model": "m1"}).encode())
    response = asyncio.run(forward_messages(request))
    assert response.status_code == 503


def test_forward_messages_missing_model() -> None:
    save_config(Config(proxy_enabled=True))
    request = _request_with_body(json.dumps({"messages": []}).encode())
    response = asyncio.run(forward_messages(request))
    assert response.status_code == 400


def test_forward_messages_unknown_model() -> None:
    save_config(Config(proxy_enabled=True))
    request = _request_with_body(json.dumps({"model": "unknown"}).encode())
    response = asyncio.run(forward_messages(request))
    assert response.status_code == 404


def test_forward_messages_missing_key() -> None:
    save_config(
        Config(
            proxy_enabled=True,
            vendors={"v1": VendorProfile(base_url="https://api.example.com", model="m1")},
        )
    )
    request = _request_with_body(json.dumps({"model": "m1"}).encode())
    response = asyncio.run(forward_messages(request))
    assert response.status_code == 401


def test_forward_messages_success() -> None:
    save_config(
        Config(
            proxy_enabled=True,
            vendors={"v1": VendorProfile(base_url="https://api.example.com", model="m1")},
        )
    )
    set_key("v1", "sk-secret")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.aiter_raw.return_value = _async_iter([b'{"ok": true}'])

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_stream_ctx
    mock_client.aclose = AsyncMock()

    with patch("claudeapikey.proxy.httpx.AsyncClient", return_value=mock_client):
        request = _request_with_body(json.dumps({"model": "m1"}).encode())
        response = asyncio.run(forward_messages(request))

    assert response.status_code == 200
    mock_client.stream.assert_called_once()
    call_kwargs = mock_client.stream.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer sk-secret"
    assert call_kwargs["content"] == json.dumps({"model": "m1"}).encode()
