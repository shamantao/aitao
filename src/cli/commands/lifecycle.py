"""
Service lifecycle management (start/stop/restart all AItao services).

Provides high-level commands to manage all AItao services as a single unit.
Useful for users who don't want to manage individual services.

Commands:
  aitao start   - Start all AItao services (Meilisearch, Worker)
  aitao stop    - Stop all AItao services
  aitao restart - Restart all services
"""

import sys
import time
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli.utils import console, success, error, warning, info, status_line

app = typer.Typer(help="Service lifecycle management")


def _run_command(name: str, command: list, timeout: int = 30) -> bool:
    """
    Run a command and return success status.
    
    Args:
        name: Display name for the service
        command: Command and args to run
        timeout: Timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Live(
            Spinner("dots", text=f"[cyan]{name}[/cyan]...", console=console),
            console=console,
            transient=True,
        ):
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        
        if result.returncode == 0:
            status_line(name, "OK", ok=True)
            return True
        else:
            status_line(name, f"Failed: {result.stderr[:50]}", ok=False)
            return False
    except subprocess.TimeoutExpired:
        status_line(name, f"Timeout ({timeout}s)", ok=False)
        return False
    except Exception as e:
        status_line(name, f"Error: {str(e)[:50]}", ok=False)
        return False


def _check_service_health(name: str, check_cmd: list, timeout: int = 5) -> bool:
    """
    Check if a service is healthy.
    
    Args:
        name: Display name
        check_cmd: Command to check health
        timeout: Timeout in seconds
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except Exception:
        return False


@app.command()
def start(verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")):
    """
    Start all AItao services.
    
    Starts:
    - Meilisearch (full-text search)
    - Background worker (document processing queue)
    
    After starting, services may take a few seconds to be fully ready.
    """
    info("Starting all AItao services...")
    console.print()
    
    all_success = True
    
    # Start Meilisearch
    if not _run_command(
        "Meilisearch",
        ["brew", "services", "start", "meilisearch"],
        timeout=30
    ):
        all_success = False
    
    # Start Worker
    if not _run_command(
        "Background Worker",
        [sys.executable, "-m", "src.cli.worker", "start"],
        timeout=30
    ):
        all_success = False
    
    console.print()
    
    if all_success:
        success("All services started ✓")
        info("Services may take a moment to be fully ready.")
        console.print()
        info("Check status with: ./aitao.sh status")
    else:
        warning("Some services failed to start. Check above for details.")
        raise typer.Exit(1)


@app.command()
def stop(verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")):
    """
    Stop all AItao services.
    
    Stops:
    - Background worker (document processing daemon)
    - Meilisearch (full-text search server)
    
    Services will be gracefully shut down.
    """
    info("Stopping all AItao services...")
    console.print()
    
    all_success = True
    
    # Stop Worker first (it may be processing)
    if not _run_command(
        "Background Worker",
        [sys.executable, "-m", "src.cli.worker", "stop"],
        timeout=30
    ):
        all_success = False
    
    # Stop Meilisearch
    if not _run_command(
        "Meilisearch",
        ["brew", "services", "stop", "meilisearch"],
        timeout=30
    ):
        all_success = False
    
    console.print()
    
    if all_success:
        success("All services stopped ✓")
    else:
        warning("Some services failed to stop. Check above for details.")
        raise typer.Exit(1)


@app.command()
def restart(verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")):
    """
    Restart all AItao services.
    
    Equivalent to:
    1. Stop all services
    2. Wait a moment
    3. Start all services
    
    Useful after configuration changes.
    """
    info("Restarting all AItao services...")
    console.print()
    
    # Stop
    stop_cmd = [sys.executable, "-m", "cli", "lifecycle", "stop"]
    try:
        subprocess.run(stop_cmd, capture_output=True, timeout=60)
    except Exception:
        pass  # Continue anyway
    
    # Wait
    info("Waiting for services to fully stop...")
    time.sleep(3)
    console.print()
    
    # Start
    start_cmd = [sys.executable, "-m", "cli", "lifecycle", "start"]
    try:
        result = subprocess.run(start_cmd, capture_output=True, timeout=60)
        if result.returncode == 0:
            success("Services restarted ✓")
        else:
            error("Failed to restart services")
            raise typer.Exit(1)
    except Exception as e:
        error(f"Error restarting: {e}")
        raise typer.Exit(1)


# Register in main app (will be done in main.py)
