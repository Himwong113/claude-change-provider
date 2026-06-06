"""Systemd user service management for claudeapikey serve."""

import shutil
import subprocess
import sys
from pathlib import Path

from platformdirs import user_config_dir

SERVICE_NAME = "claudeapikey"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_FILE = SYSTEMD_USER_DIR / f"{SERVICE_NAME}.service"

UNIT_TEMPLATE = """[Unit]
Description=claudeapikey web dashboard
After=network.target

[Service]
Type=simple
ExecStart={python} -m uvicorn claudeapikey.web_server:app --host 127.0.0.1 --port {port}
Restart=on-failure
Environment=PATH={path}

[Install]
WantedBy=default.target
"""


def _systemctl(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "--user"] + args,
        capture_output=True,
        text=True,
    )


def install_service(port: int = 8787) -> Path:
    """Generate and install the systemd user service unit."""
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    python_path = shutil.which("python") or shutil.which("python3") or sys.executable
    path_env = shutil.which("claude") or ""
    if path_env:
        path_env = str(Path(path_env).parent)
    content = UNIT_TEMPLATE.format(
        python=python_path,
        port=port,
        path=path_env,
    )
    SERVICE_FILE.write_text(content)
    _systemctl(["daemon-reload"])
    return SERVICE_FILE


def uninstall_service() -> None:
    """Remove the systemd user service unit."""
    if SERVICE_FILE.exists():
        stop_service()
        disable_service()
        SERVICE_FILE.unlink()
        _systemctl(["daemon-reload"])


def start_service() -> None:
    _systemctl(["start", SERVICE_NAME])


def stop_service() -> None:
    _systemctl(["stop", SERVICE_NAME])


def enable_service() -> None:
    _systemctl(["enable", SERVICE_NAME])


def disable_service() -> None:
    _systemctl(["disable", SERVICE_NAME])


def service_status() -> dict[str, str | bool]:
    """Return the service status."""
    result = _systemctl(["status", SERVICE_NAME])
    active = "Active: active (running)" in result.stdout
    enabled = _systemctl(["is-enabled", SERVICE_NAME]).returncode == 0
    return {
        "installed": SERVICE_FILE.exists(),
        "active": active,
        "enabled": enabled,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def is_systemctl_available() -> bool:
    return shutil.which("systemctl") is not None
