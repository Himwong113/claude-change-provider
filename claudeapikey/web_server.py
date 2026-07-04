"""FastAPI web server for claudeapikey dashboard."""

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response

from claudeapikey.config_store import load_config, save_config
from claudeapikey.doctor import run_doctor
from claudeapikey.env_builder import build_env
from claudeapikey.models import Config, VendorProfile
from claudeapikey.proxy import forward_messages
from claudeapikey.secret_store import (
    delete_key,
    get_key,
    mask_key,
    set_key,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app = FastAPI(title="claudeapikey")

# ---------------------------------------------------------------------------
# CSRF protection: reject state-changing requests whose Origin header does not
# match a localhost origin.  Browsers always send Origin on cross-origin
# POST/PUT/DELETE requests, so this blocks CSRF from remote sites while still
# allowing direct curl / CLI calls (which send no Origin header).
# ---------------------------------------------------------------------------
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_LOCALHOST_ORIGINS = {
    "http://127.0.0.1",
    "http://localhost",
}


@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.method not in _SAFE_METHODS:
        if request.url.path.startswith("/v1/"):
            return await call_next(request)
        origin = request.headers.get("origin")
        if origin is not None:
            # Strip port so http://127.0.0.1:8787 and http://localhost:8787 both pass
            origin_base = origin.rsplit(":", 1)[0] if origin.count(":") > 1 else origin
            if origin_base not in _LOCALHOST_ORIGINS:
                from fastapi.responses import JSONResponse as _JSONResponse
                return _JSONResponse({"detail": "CSRF check failed"}, status_code=403)
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    config = load_config()
    vendors = []
    for name, profile in config.vendors.items():
        k = get_key(name)
        vendors.append({
            "name": name,
            "model": profile.model,
            "base_url": profile.base_url or "(official)",
            "auth_env": profile.auth_env,
            "official": profile.official,
            "extra_env": profile.extra_env,
            "key_set": k is not None,
            "key_masked": mask_key(k) if k else "not set",
        })
    return templates.TemplateResponse(
        request,
        "index.html",
        {"vendors": vendors, "active_vendor": config.active_vendor},
    )


@app.get("/api/vendors")
async def api_list_vendors() -> JSONResponse:
    config = load_config()
    vendors = []
    for name, profile in config.vendors.items():
        k = get_key(name)
        vendors.append({
            "name": name,
            "model": profile.model,
            "base_url": profile.base_url,
            "auth_env": profile.auth_env,
            "official": profile.official,
            "extra_env": profile.extra_env,
            "key_set": k is not None,
            "key_masked": mask_key(k) if k else None,
        })
    return JSONResponse({"vendors": vendors, "active_vendor": config.active_vendor})


@app.post("/api/vendors/{vendor}")
async def api_add_vendor(
    vendor: str,
    base_url: str | None = Form(None),
    auth_env: str = Form("ANTHROPIC_API_KEY"),
    model: str = Form(...),
    official: bool = Form(False),
    extra_env: str = Form(""),
) -> JSONResponse:
    config = load_config()
    if vendor in config.vendors:
        raise HTTPException(status_code=409, detail="Vendor already exists")

    parsed_extra: dict[str, str] = {}
    for line in extra_env.strip().splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        parsed_extra[k.strip()] = v.strip()

    try:
        profile = VendorProfile(
            base_url=base_url or None,
            auth_env=auth_env,  # type: ignore[arg-type]
            model=model,
            official=official,
            extra_env=parsed_extra,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    config.vendors[vendor] = profile
    save_config(config)
    return JSONResponse({"status": "ok", "vendor": vendor})


@app.put("/api/vendors/{vendor}")
async def api_edit_vendor(
    vendor: str,
    base_url: str | None = Form(None),
    auth_env: str | None = Form(None),
    model: str | None = Form(None),
    official: bool | None = Form(None),
    extra_env: str | None = Form(None),
    key: str | None = Form(None),
) -> JSONResponse:
    config = load_config()
    if vendor not in config.vendors:
        raise HTTPException(status_code=404, detail="Vendor not found")

    profile = config.vendors[vendor]
    if base_url is not None:
        profile.base_url = base_url or None
    if auth_env is not None:
        profile.auth_env = auth_env  # type: ignore[assignment]
    if model is not None:
        profile.model = model
    if official is not None:
        profile.official = official
    if extra_env is not None:
        parsed_extra: dict[str, str] = {}
        for line in extra_env.strip().splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            parsed_extra[k.strip()] = v.strip()
        profile.extra_env = parsed_extra

    try:
        profile = VendorProfile.model_validate(profile.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    config.vendors[vendor] = profile
    save_config(config)

    if key is not None:
        set_key(vendor, key)

    return JSONResponse({"status": "ok", "vendor": vendor})


@app.delete("/api/vendors/{vendor}")
async def api_remove_vendor(vendor: str) -> JSONResponse:
    config = load_config()
    if vendor not in config.vendors:
        raise HTTPException(status_code=404, detail="Vendor not found")
    del config.vendors[vendor]
    if config.active_vendor == vendor:
        config.active_vendor = None
    save_config(config)
    return JSONResponse({"status": "ok"})


@app.post("/api/vendors/{vendor}/key")
async def api_set_key(vendor: str, key: str = Form(...)) -> JSONResponse:
    config = load_config()
    if vendor not in config.vendors:
        raise HTTPException(status_code=404, detail="Vendor not found")
    set_key(vendor, key)
    return JSONResponse({"status": "ok"})


@app.delete("/api/vendors/{vendor}/key")
async def api_delete_key(vendor: str) -> JSONResponse:
    config = load_config()
    if vendor not in config.vendors:
        raise HTTPException(status_code=404, detail="Vendor not found")
    delete_key(vendor)
    return JSONResponse({"status": "ok"})


@app.get("/api/vendors/{vendor}/env")
async def api_env(vendor: str) -> JSONResponse:
    config = load_config()
    if vendor not in config.vendors:
        raise HTTPException(status_code=404, detail="Vendor not found")
    profile = config.vendors[vendor]
    try:
        env = build_env(vendor)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Mask the auth key — the web UI is display-only; never return the raw key over HTTP.
    lines = []
    for k, v in env.items():
        display_v = mask_key(v) if k == profile.auth_env else v
        escaped = display_v.replace("'", "'\"'\"'")
        lines.append(f"export {k}='{escaped}'")
    exports = "\n".join(lines)
    return JSONResponse({"vendor": vendor, "exports": exports})


@app.get("/api/doctor")
async def api_doctor() -> JSONResponse:
    result = run_doctor()
    return JSONResponse({
        "ok": result.ok,
        "messages": [{"status": s, "detail": d} for s, d in result.messages],
    })


# ---------------------------------------------------------------------------
# Proxy routes
# ---------------------------------------------------------------------------


@app.post("/v1/messages")
async def proxy_messages(request: Request) -> Response:
    """Anthropic-compatible messages endpoint that routes by model."""
    return await forward_messages(request)


@app.get("/v1/health")
async def proxy_health() -> JSONResponse:
    return JSONResponse({"status": "ok", "proxy": True})


def _proxy_routes(config: Config) -> list[dict[str, str]]:
    return [
        {"model": profile.model, "vendor": name}
        for name, profile in config.vendors.items()
        if profile.model
    ]


@app.get("/api/proxy/status")
async def api_proxy_status() -> JSONResponse:
    config = load_config()
    return JSONResponse({
        "enabled": config.proxy_enabled,
        "url": f"http://localhost:{config.proxy_port}",
        "routes": _proxy_routes(config),
        "tiers": config.proxy_tiers,
    })


@app.post("/api/proxy/enable")
async def api_proxy_enable() -> JSONResponse:
    config = load_config()
    config.proxy_enabled = True
    save_config(config)
    return JSONResponse({"enabled": True})


@app.post("/api/proxy/disable")
async def api_proxy_disable() -> JSONResponse:
    config = load_config()
    config.proxy_enabled = False
    save_config(config)
    return JSONResponse({"enabled": False})


@app.put("/api/proxy/tiers")
async def api_proxy_tiers(tiers: str = Form(...)) -> JSONResponse:
    """Update tier aliases. Expects one KEY=VALUE per line."""
    parsed: dict[str, str] = {}
    for line in tiers.strip().splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        parsed[k.strip()] = v.strip()

    config = load_config()
    config.proxy_tiers = parsed
    save_config(config)
    return JSONResponse({"tiers": config.proxy_tiers})

