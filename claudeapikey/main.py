"""Typer CLI entry point for claudeapikey."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from claudeapikey import __version__
from claudeapikey.claude_settings import apply_proxy_settings, apply_vendor, reset_settings
from claudeapikey.config_store import (
    config_exists,
    get_config_path,
    load_config,
    remove_config,
    save_config,
)
from claudeapikey.doctor import run_doctor
from claudeapikey.env_builder import build_env, build_env_exports
from claudeapikey.models import Config, VendorProfile
from claudeapikey.runner import find_claude, run_vendor
from claudeapikey.systemd_service import (
    SERVICE_NAME,
    disable_service,
    enable_service,
    install_service,
    is_systemctl_available,
    service_status,
    start_service,
    stop_service,
    uninstall_service,
)
from claudeapikey.secret_store import (
    check_keyring_available,
    delete_key,
    get_key,
    key_exists,
    mask_key,
    set_key,
)

app = typer.Typer(
    name="claudeapikey",
    help="Claude Code vendor switcher CLI",
    no_args_is_help=True,
)
console = Console()

# Sub-apps
key_app = typer.Typer(name="key", help="Manage API keys")
app.add_typer(key_app)

service_app = typer.Typer(name="service", help="Manage systemd service")
app.add_typer(service_app)

proxy_app = typer.Typer(name="proxy", help="Manage model-routing proxy")
app.add_typer(proxy_app)


@app.command()
def install() -> None:
    """Initialize claudeapikey."""
    claude_found = find_claude() is not None
    config_path = get_config_path()
    keyring_ok = check_keyring_available()

    if not config_exists():
        save_config(Config())

    console.print("[bold]Claude API Key Manager[/bold]\n")
    console.print(f"Claude Code found: {'[green]yes[/green]' if claude_found else '[yellow]no[/yellow]'}")
    console.print(f"Config path: {config_path}")
    console.print(f"Secret store: {'[green]OS keyring[/green]' if keyring_ok else '[yellow]unavailable[/yellow]'}")
    console.print("\n[green]Done.[/green]\n")
    console.print("Next:")
    console.print("  [cyan]claudeapikey add deepseek[/cyan]")
    console.print("  [cyan]claudeapikey key set deepseek[/cyan]")
    console.print("  [cyan]claudeapikey run deepseek[/cyan]")


# Known vendor presets
KNOWN_VENDORS: dict[str, dict[str, str | bool | dict[str, str]]] = {
    "kimi": {
        "base_url": "https://api.kimi.com/coding/",
        "auth_env": "ANTHROPIC_AUTH_TOKEN",
        "model": "kimi-k2.6",
        "official": False,
        "extra_env": {
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-k2.6",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-k2.6",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "kimi-k2.6",
            "CLAUDE_CODE_SUBAGENT_MODEL": "kimi-k2.6",
            "ENABLE_TOOL_SEARCH": "false",
        },
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/anthropic",
        "auth_env": "ANTHROPIC_API_KEY",
        "model": "deepseek-chat",
        "official": False,
        "extra_env": {},
    },
    "official": {
        "base_url": None,
        "auth_env": "ANTHROPIC_API_KEY",
        "model": "claude-3-5-sonnet-20241022",
        "official": True,
        "extra_env": {},
    },
}


@app.command()
def add(
    vendor: str = typer.Argument(..., help="Vendor name (known presets: kimi, deepseek, official)"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="API base URL"),
    auth_env: Optional[str] = typer.Option(None, "--auth-env", help="Auth env var name"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name"),
    official: Optional[bool] = typer.Option(None, "--official", help="Mark as official Anthropic API"),
    extra_env: Optional[list[str]] = typer.Option(
        None,
        "--extra-env",
        help="Extra env vars in KEY=VALUE format (can be repeated)",
    ),
) -> None:
    """Add a new vendor profile."""
    config = load_config()
    if vendor in config.vendors:
        console.print(f"[red]Vendor '{vendor}' already exists. Use 'edit' to modify.[/red]")
        raise typer.Exit(1)

    # Apply known vendor preset as defaults
    preset = KNOWN_VENDORS.get(vendor, {})
    effective_base_url = base_url if base_url is not None else preset.get("base_url")
    effective_auth_env = auth_env if auth_env is not None else preset.get("auth_env", "ANTHROPIC_API_KEY")
    effective_model = model if model is not None else preset.get("model")
    effective_official = official if official is not None else preset.get("official", False)

    parsed_extra: dict[str, str] = {}
    if extra_env:
        for item in extra_env:
            if "=" not in item:
                console.print(f"[red]Invalid extra-env format: {item} (expected KEY=VALUE)[/red]")
                raise typer.Exit(1)
            k, v = item.split("=", 1)
            parsed_extra[k] = v
    # Merge preset extra_env with user-provided extra_env (user overrides preset)
    preset_extra = preset.get("extra_env", {})
    if isinstance(preset_extra, dict):
        merged_extra = dict(preset_extra)
        merged_extra.update(parsed_extra)
        parsed_extra = merged_extra

    if effective_model is None:
        console.print("[red]--model is required for unknown vendors.[/red]")
        raise typer.Exit(1)

    try:
        profile = VendorProfile(
            base_url=effective_base_url,  # type: ignore[arg-type]
            auth_env=effective_auth_env,  # type: ignore[arg-type]
            model=effective_model,
            official=effective_official,  # type: ignore[arg-type]
            extra_env=parsed_extra,
        )
    except Exception as e:
        console.print(f"[red]Invalid profile: {e}[/red]")
        raise typer.Exit(1)

    config.vendors[vendor] = profile
    save_config(config)
    console.print(f"[green]Vendor '{vendor}' added.[/green]")
    if vendor in KNOWN_VENDORS:
        console.print(f"[dim]Used preset defaults for '{vendor}'.[/dim]")
    console.print(f"Set the API key: [cyan]claudeapikey key set {vendor}[/cyan]")


@app.command()
def edit(
    vendor: str = typer.Argument(..., help="Vendor name"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="API base URL"),
    auth_env: Optional[str] = typer.Option(None, "--auth-env", help="Auth env var name"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name"),
    official: Optional[bool] = typer.Option(None, "--official", help="Mark as official Anthropic API"),
    extra_env: Optional[list[str]] = typer.Option(
        None,
        "--extra-env",
        help="Extra env vars in KEY=VALUE format (can be repeated)",
    ),
) -> None:
    """Edit an existing vendor profile."""
    config = load_config()
    if vendor not in config.vendors:
        console.print(f"[red]Vendor '{vendor}' not found.[/red]")
        raise typer.Exit(1)

    profile = config.vendors[vendor]
    if base_url is not None:
        profile.base_url = base_url
    if auth_env is not None:
        profile.auth_env = auth_env  # type: ignore[assignment]
    if model is not None:
        profile.model = model
    if official is not None:
        profile.official = official
    if extra_env is not None:
        parsed_extra: dict[str, str] = {}
        for item in extra_env:
            if "=" not in item:
                console.print(f"[red]Invalid extra-env format: {item}[/red]")
                raise typer.Exit(1)
            k, v = item.split("=", 1)
            parsed_extra[k] = v
        profile.extra_env = parsed_extra

    # Re-validate
    try:
        profile = VendorProfile.model_validate(profile.model_dump())
    except Exception as e:
        console.print(f"[red]Invalid profile: {e}[/red]")
        raise typer.Exit(1)

    config.vendors[vendor] = profile
    save_config(config)
    console.print(f"[green]Vendor '{vendor}' updated.[/green]")


@app.command("list")
def list_vendors() -> None:
    """List all vendor profiles."""
    config = load_config()
    if not config.vendors:
        console.print("No vendors configured.")
        return

    table = Table(title="Vendors")
    table.add_column("Name", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Base URL", style="dim")
    table.add_column("Auth", style="yellow")
    table.add_column("Key", style="magenta")

    for name, profile in config.vendors.items():
        has_key = "✓" if key_exists(name) else "✗"
        table.add_row(
            name,
            profile.model,
            profile.base_url or "(official)",
            profile.auth_env,
            has_key,
        )
    console.print(table)


@app.command()
def show(
    vendor: str = typer.Argument(..., help="Vendor name"),
) -> None:
    """Show a vendor profile."""
    config = load_config()
    profile = config.vendors.get(vendor)
    if profile is None:
        console.print(f"[red]Vendor '{vendor}' not found.[/red]")
        raise typer.Exit(1)

    key = get_key(vendor)
    key_display = mask_key(key) if key else "[red]not set[/red]"

    table = Table(title=f"Vendor: {vendor}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Model", profile.model)
    table.add_row("Base URL", profile.base_url or "(official)")
    table.add_row("Auth Env", profile.auth_env)
    table.add_row("Official", "yes" if profile.official else "no")
    table.add_row("API Key", key_display)
    if profile.extra_env:
        table.add_row("Extra Env", "\n".join(f"{k}={v}" for k, v in profile.extra_env.items()))

    console.print(table)


@app.command()
def remove(
    vendor: str = typer.Argument(..., help="Vendor name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    delete_key: bool = typer.Option(False, "--delete-key", help="Also delete stored API key"),
) -> None:
    """Remove a vendor profile."""
    config = load_config()
    if vendor not in config.vendors:
        console.print(f"[red]Vendor '{vendor}' not found.[/red]")
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Remove vendor '{vendor}'?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit(0)

    del config.vendors[vendor]
    if config.active_vendor == vendor:
        config.active_vendor = None
    save_config(config)

    if delete_key:
        from claudeapikey.secret_store import delete_key as _delete_key

        _delete_key(vendor)
        console.print(f"[green]Vendor '{vendor}' removed and key deleted.[/green]")
    else:
        console.print(f"[green]Vendor '{vendor}' removed.[/green]")


# Key subcommands


@key_app.command("set")
def key_set(
    vendor: str = typer.Argument(..., help="Vendor name"),
) -> None:
    """Set the API key for a vendor."""
    config = load_config()
    if vendor not in config.vendors:
        console.print(f"[red]Vendor '{vendor}' not found. Add it first.[/red]")
        raise typer.Exit(1)

    key = typer.prompt("API key", hide_input=True)

    set_key(vendor, key)
    console.print(f"[green]API key saved for '{vendor}'.[/green]")


@key_app.command("get")
def key_get(
    vendor: str = typer.Argument(..., help="Vendor name"),
    raw: bool = typer.Option(False, "--raw", help="Print raw key only"),
) -> None:
    """Get the API key for a vendor."""
    k = get_key(vendor)
    if k is None:
        if raw:
            pass  # exit silently with non-zero
        else:
            console.print(f"[red]No key found for '{vendor}'.[/red]")
        raise typer.Exit(1)

    if raw:
        console.print(k, end="")
    else:
        console.print(f"Key for '{vendor}': {mask_key(k)}")


@key_app.command("delete")
def key_delete(
    vendor: str = typer.Argument(..., help="Vendor name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete the API key for a vendor."""
    if not key_exists(vendor):
        console.print(f"[red]No key found for '{vendor}'.[/red]")
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Delete API key for '{vendor}'?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit(0)

    delete_key(vendor)
    console.print(f"[green]API key for '{vendor}' deleted.[/green]")


@key_app.command("copy")
def key_copy(
    vendor: str = typer.Argument(..., help="Vendor name"),
) -> None:
    """Copy the API key to the clipboard."""
    k = get_key(vendor)
    if k is None:
        console.print(f"[red]No key found for '{vendor}'.[/red]")
        raise typer.Exit(1)

    try:
        import pyperclip

        pyperclip.copy(k)
        console.print(f"[green]API key for '{vendor}' copied to clipboard.[/green]")
    except ImportError:
        console.print(f"[yellow]pyperclip not installed. Raw key:[/yellow] {mask_key(k)}")
        console.print("Install pyperclip for clipboard support: pip install pyperclip")


@app.command()
def env(
    vendor: str = typer.Argument(..., help="Vendor name"),
) -> None:
    """Print shell export statements for a vendor."""
    try:
        exports = build_env_exports(vendor)
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(exports)


@app.command()
def run(
    vendor: str = typer.Argument(..., help="Vendor name"),
    extra_args: Optional[list[str]] = typer.Argument(None, help="Extra arguments for claude"),
) -> None:
    """Run Claude Code with the vendor environment."""
    try:
        run_vendor(vendor, extra_args or [])
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def use(
    vendor: str = typer.Argument(..., help="Vendor name"),
    local: bool = typer.Option(False, "--local", help="Apply to project-local settings"),
    global_: bool = typer.Option(False, "--global", help="Apply to global settings"),
) -> None:
    """Apply a vendor to Claude Code settings."""
    if not local and not global_:
        console.print("[red]Must specify --local or --global[/red]")
        raise typer.Exit(1)
    try:
        apply_vendor(vendor, local=local, global_=global_)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    scope = "local" if local else "global"
    console.print(f"[green]Applied '{vendor}' to Claude Code {scope} settings.[/green]")


@app.command()
def reset(
    local: bool = typer.Option(False, "--local", help="Reset project-local settings"),
    global_: bool = typer.Option(False, "--global", help="Reset global settings"),
) -> None:
    """Remove managed fields from Claude Code settings."""
    if not local and not global_:
        console.print("[red]Must specify --local or --global[/red]")
        raise typer.Exit(1)
    try:
        reset_settings(local=local, global_=global_)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    scope = "local" if local else "global"
    console.print(f"[green]Reset Claude Code {scope} settings.[/green]")


@app.command()
def current() -> None:
    """Show the currently active vendor."""
    config = load_config()
    if config.active_vendor:
        console.print(f"Active vendor: [cyan]{config.active_vendor}[/cyan]")
    else:
        console.print("No active vendor set.")


@app.command()
def doctor() -> None:
    """Run diagnostics."""
    result = run_doctor()
    console.print("[bold]Claude API Key Manager Doctor[/bold]\n")
    for status, detail in result.messages:
        color = "green" if status == "OK" else "yellow" if status == "WARN" else "red"
        console.print(f"[{color}]{status}[/{color}] {detail}")
    console.print()
    if result.ok:
        console.print("[bold green]Result: OK[/bold green]")
    else:
        console.print("[bold red]Result: Issues found[/bold red]")


@app.command()
def uninstall(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove claudeapikey configuration and all stored keys."""
    if not yes:
        confirm = typer.confirm("Remove all vendors and API keys? This cannot be undone.")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit(0)

    config = load_config()
    for vendor in list(config.vendors.keys()):
        delete_key(vendor)

    remove_config()
    console.print("[green]claudeapikey uninstalled.[/green]")


def _find_pids_on_port(port: int) -> list[int]:
    """Find all PIDs of processes listening on the given port."""
    import subprocess

    for cmd in [f"lsof -ti :{port}", f"fuser {port}/tcp 2>/dev/null"]:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pids = []
                for line in result.stdout.strip().splitlines():
                    for token in line.split():
                        try:
                            pids.append(int(token))
                        except ValueError:
                            continue
                return list(dict.fromkeys(pids))  # dedupe preserving order
        except Exception:
            continue
    return []


def _is_port_free(host: str, port: int) -> bool:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        return sock.connect_ex((host, port)) != 0
    finally:
        sock.close()


@app.command()
def serve(
    port: int = typer.Option(8787, "--port", "-p", help="Port to bind on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind on"),
    kill: bool = typer.Option(False, "--kill", "-k", help="Kill existing process on the port before starting"),
) -> None:
    """Start the web dashboard."""
    import socket
    import uvicorn

    # Check if port is already in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    in_use = sock.connect_ex((host, port)) == 0
    sock.close()

    if in_use:
        existing_pids = _find_pids_on_port(port)
        if existing_pids:
            pid_list = ", ".join(str(p) for p in existing_pids)
            console.print(f"[yellow]Port {port} is already in use by PID(s): {pid_list}[/yellow]")
            if kill:
                import os
                import signal
                import time

                # Phase 1: SIGTERM all PIDs
                for pid in existing_pids:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        console.print(f"[red]Permission denied to kill PID {pid}. Try: sudo kill -9 {pid}[/red]")
                        raise typer.Exit(1)
                console.print(f"[green]Sent SIGTERM to PID(s): {pid_list}[/green]")

                # Wait up to 3s for graceful exit
                for _ in range(15):
                    time.sleep(0.2)
                    if _is_port_free(host, port):
                        break
                else:
                    # Phase 2: SIGKILL whatever is still on the port
                    remaining = _find_pids_on_port(port)
                    if remaining:
                        for pid in remaining:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        console.print(f"[green]Sent SIGKILL to remaining PID(s): {', '.join(str(p) for p in remaining)}[/green]")
                        # Wait for port release
                        for _ in range(20):
                            time.sleep(0.2)
                            if _is_port_free(host, port):
                                break
                # Final check
                if not _is_port_free(host, port):
                    console.print(f"[red]Port {port} is still in use after kill attempts.[/red]")
                    console.print("Try manually: sudo fuser -k 8787/tcp")
                    raise typer.Exit(1)
            else:
                console.print(f"[red]Port {port} is already in use.[/red]")
                console.print(f"Run with --kill to replace it, or manually: kill -9 {pid_list}")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Port {port} is already in use by an unknown process.[/red]")
            console.print("Run with --kill to attempt replacement, or choose a different port with --port")
            raise typer.Exit(1)

    if host != "127.0.0.1":
        console.print("[yellow]Warning: Binding to non-loopback address is not recommended for security.[/yellow]")
    console.print(f"[green]Starting claudeapikey dashboard at http://{host}:{port}[/green]")
    uvicorn.run("claudeapikey.web_server:app", host=host, port=port, log_level="info")


# Service subcommands


@service_app.command("install")
def service_install(
    port: int = typer.Option(8787, "--port", "-p", help="Dashboard port"),
    start: bool = typer.Option(True, "--start/--no-start", help="Start service after install"),
    enable: bool = typer.Option(True, "--enable/--no-enable", help="Enable service on boot"),
) -> None:
    """Install the systemd user service for the dashboard."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found. systemd is required.[/red]")
        raise typer.Exit(1)

    path = install_service(port=port)
    console.print(f"[green]Service installed: {path}[/green]")

    if enable:
        enable_service()
        console.print("[green]Service enabled.[/green]")
    if start:
        start_service()
        console.print("[green]Service started.[/green]")
    console.print(f"\nDashboard will be available at [cyan]http://127.0.0.1:{port}[/cyan]")
    console.print("\nManage with:")
    console.print(f"  [cyan]systemctl --user status {SERVICE_NAME}[/cyan]")
    console.print(f"  [cyan]systemctl --user start {SERVICE_NAME}[/cyan]")
    console.print(f"  [cyan]systemctl --user stop {SERVICE_NAME}[/cyan]")


@service_app.command("uninstall")
def service_uninstall(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove the systemd user service."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found.[/red]")
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm("Remove the claudeapikey systemd service?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit(0)

    uninstall_service()
    console.print("[green]Service uninstalled.[/green]")


@service_app.command("start")
def service_start() -> None:
    """Start the systemd user service."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found.[/red]")
        raise typer.Exit(1)
    start_service()
    console.print("[green]Service started.[/green]")


@service_app.command("stop")
def service_stop() -> None:
    """Stop the systemd user service."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found.[/red]")
        raise typer.Exit(1)
    stop_service()
    console.print("[green]Service stopped.[/green]")


@service_app.command("enable")
def service_enable() -> None:
    """Enable the systemd user service to start on boot."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found.[/red]")
        raise typer.Exit(1)
    enable_service()
    console.print("[green]Service enabled.[/green]")


@service_app.command("disable")
def service_disable() -> None:
    """Disable the systemd user service from starting on boot."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found.[/red]")
        raise typer.Exit(1)
    disable_service()
    console.print("[green]Service disabled.[/green]")


@service_app.command("status")
def service_status_cmd() -> None:
    """Show the systemd service status."""
    if not is_systemctl_available():
        console.print("[red]systemctl not found.[/red]")
        raise typer.Exit(1)

    status = service_status()
    table = Table(title="Service Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Installed", "[green]yes[/green]" if status["installed"] else "[red]no[/red]")
    table.add_row("Active", "[green]yes[/green]" if status["active"] else "[red]no[/red]")
    table.add_row("Enabled", "[green]yes[/green]" if status["enabled"] else "[red]no[/red]")

    console.print(table)

    if status["stdout"]:
        console.print(status["stdout"])


@proxy_app.command("enable")
def proxy_enable(
    port: int = typer.Option(8787, "--port", "-p", help="Proxy port"),
    local: bool = typer.Option(False, "--local", help="Apply to project-local settings"),
    global_: bool = typer.Option(False, "--global", help="Apply to global settings"),
) -> None:
    """Enable proxy mode and optionally apply it to Claude Code settings."""
    config = load_config()
    config.proxy_enabled = True
    if port != config.proxy_port:
        config.proxy_port = port
    save_config(config)
    console.print(f"[green]Proxy mode enabled on port {port}.[/green]")
    if local or global_:
        try:
            apply_proxy_settings(port=port, local=local, global_=global_)
            scope = "local" if local else "global"
            console.print(f"[green]Applied proxy settings to Claude Code {scope} settings.[/green]")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)


@proxy_app.command("disable")
def proxy_disable() -> None:
    """Disable proxy mode."""
    config = load_config()
    config.proxy_enabled = False
    save_config(config)
    console.print("[green]Proxy mode disabled.[/green]")


@proxy_app.command("status")
def proxy_status_cmd() -> None:
    """Show proxy status and routing table."""
    config = load_config()
    table = Table(title="Proxy Routes")
    table.add_column("Model", style="cyan")
    table.add_column("Vendor", style="green")
    table.add_column("Base URL", style="dim")
    for name, profile in config.vendors.items():
        if profile.model:
            table.add_row(profile.model, name, profile.base_url or "(official)")
    console.print(table)
    console.print(f"Proxy enabled: {'[green]yes[/green]' if config.proxy_enabled else '[red]no[/red]'}")
    console.print(f"Proxy URL: http://localhost:{config.proxy_port}")
    if config.proxy_tiers:
        console.print("Tier aliases:")
        for tier, model in config.proxy_tiers.items():
            console.print(f"  {tier}: {model}")


@proxy_app.command("apply")
def proxy_apply(
    port: int = typer.Option(8787, "--port", "-p", help="Proxy port"),
    local: bool = typer.Option(False, "--local", help="Apply to project-local settings"),
    global_: bool = typer.Option(False, "--global", help="Apply to global settings"),
) -> None:
    """Write proxy settings to Claude Code settings without toggling proxy mode."""
    if not local and not global_:
        console.print("[red]Must specify --local or --global[/red]")
        raise typer.Exit(1)
    try:
        apply_proxy_settings(port=port, local=local, global_=global_)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    scope = "local" if local else "global"
    console.print(f"[green]Applied proxy settings to Claude Code {scope} settings.[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
