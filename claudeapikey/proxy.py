"""Anthropic-compatible request proxy that routes by model to stored vendors."""

import json

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from claudeapikey.config_store import load_config
from claudeapikey.models import Config, VendorProfile
from claudeapikey.secret_store import get_key

_OFFICIAL_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "authorization",
    # Strip any client-provided API key headers; the proxy injects the real
    # vendor key before forwarding. This prevents the dummy "local-proxy" key
    # (or a stale token) from reaching upstream providers.
    "x-api-key",
}


def extract_model(body: bytes) -> str | None:
    """Extract the model name from an Anthropic-style request body."""
    try:
        data = json.loads(body)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    model = data.get("model")
    if isinstance(model, str):
        return model.strip() or None
    return None


def resolve_vendor(model: str, config: Config) -> tuple[str, VendorProfile] | None:
    """Find the first vendor whose profile model matches the request model."""
    for name, profile in config.vendors.items():
        if profile.model == model:
            return name, profile
    return None


def build_target_url(vendor: VendorProfile) -> str:
    """Build the upstream messages endpoint for a vendor."""
    if vendor.official:
        return _OFFICIAL_MESSAGES_URL
    base = (vendor.base_url or "").rstrip("/")
    if not base:
        raise ValueError("non-official vendor missing base_url")
    if base.endswith("/v1/messages"):
        return base
    if base.endswith("/v1"):
        return f"{base}/messages"
    return f"{base}/v1/messages"


def get_auth_header(key: str, vendor: VendorProfile | None = None) -> dict[str, str]:
    """Return the auth header for the upstream request."""
    if vendor is not None and vendor.auth_env == "ANTHROPIC_API_KEY":
        return {"x-api-key": key}
    return {"Authorization": f"Bearer {key}"}


def _forwardable_headers(request: Request) -> dict[str, str]:
    """Return request headers safe to forward to the upstream API."""
    headers: dict[str, str] = {}
    for name, value in request.headers.items():
        if name.lower() in _HOP_BY_HOP:
            continue
        headers[name] = value
    return headers


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status_code)


async def forward_messages(request: Request) -> Response:
    """Receive an Anthropic-style request and forward it to the matching vendor."""
    config = load_config()
    if not config.proxy_enabled:
        return _error_response(503, "Proxy is not enabled")

    body = await request.body()
    model = extract_model(body)
    if model is None:
        return _error_response(400, "Missing or invalid model field")

    resolved = resolve_vendor(model, config)
    if resolved is None:
        available = sorted({p.model for p in config.vendors.values() if p.model})
        return _error_response(
            404,
            f"Unknown model '{model}'. Available routes: {', '.join(available)}",
        )

    vendor_name, vendor = resolved
    key = get_key(vendor_name)
    if key is None:
        return _error_response(401, f"No API key configured for vendor '{vendor_name}'")

    try:
        target_url = build_target_url(vendor)
    except ValueError as exc:
        return _error_response(500, str(exc))

    headers = _forwardable_headers(request)
    headers.update(get_auth_header(key, vendor))

    client = httpx.AsyncClient()
    stream_ctx = client.stream(
        "POST",
        target_url,
        headers=headers,
        content=body,
        timeout=300.0,
    )
    response = await stream_ctx.__aenter__()

    async def stream_body():
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        finally:
            await stream_ctx.__aexit__(None, None, None)
            await client.aclose()

    return StreamingResponse(
        stream_body(),
        status_code=response.status_code,
        headers=dict(response.headers),
    )
