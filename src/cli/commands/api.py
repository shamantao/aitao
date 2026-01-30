"""
API service management commands.

Provides CLI commands to manage the FastAPI server:
- status: Check API availability
- start: Start API server
- stop: Stop API server
"""

import sys
import socket
from pathlib import Path
from typing import Optional

import typer
import requests

# Ensure src is in path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli.utils import console, status_line, info
from cli.commands import lifecycle as lifecycle_cmd

app = typer.Typer(help="API server management")


def _get_api_base_url() -> str:
    """Build the API base URL from config."""
    port = lifecycle_cmd.get_api_port()
    return f"http://localhost:{port}"


def _check_api_health() -> tuple[bool, str, Optional[str]]:
    """Check API health endpoint."""
    base_url = _get_api_base_url()
    host = "localhost"
    port = int(base_url.rsplit(":", 1)[-1])
    try:
        with socket.create_connection((host, port), timeout=1.0):
            pass
    except OSError:
        return False, base_url, None
    try:
        response = requests.get(f"{base_url}/api/health", timeout=(1, 5))
        if response.status_code == 200:
            return True, base_url, None
        return False, base_url, f"Unhealthy ({response.status_code})"
    except requests.ReadTimeout:
        return True, base_url, "Running (slow health check)"
    except requests.RequestException as e:
        return True, base_url, f"Health check failed: {e}"


@app.command()
def status():
    """Show API server status."""
    ok, base_url, detail = _check_api_health()
    console.print("[bold]API Server[/bold]")
    if ok:
        status_line("Status", detail or "Running")
        status_line("URL", base_url)
    else:
        status_line("Status", detail or "Not running", ok=False)
        status_line("URL", base_url, ok=False)
        info("  Start with: ./aitao.sh api start")


@app.command()
def start():
    """Start the API server."""
    ok, pid = lifecycle_cmd.start_api()
    if ok:
        status_line("API", f"Started (PID {pid})")
    else:
        status_line("API", "Failed to start", ok=False)


@app.command()
def stop():
    """Stop the API server."""
    if lifecycle_cmd.stop_api():
        status_line("API", "Stopped")
    else:
        status_line("API", "Failed to stop", ok=False)
