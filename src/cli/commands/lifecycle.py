"""
Service lifecycle management (start/stop/restart all AItao services).

Provides high-level commands to manage all AItao services as a single unit.
This is the MAIN entry point for users to control AItao.

Services managed:
  1. Meilisearch    - Full-text search engine (brew services)
  2. API FastAPI    - REST API server (port 5000)
  3. Worker daemon  - Background document processing
  4. Initial scan   - Populate queue with documents on start

Commands:
  aitao start   - Start ALL services + trigger initial scan
  aitao stop    - Stop ALL services gracefully
  aitao restart - Restart all services
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn

# Ensure src is in path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli.utils import console, success, error, warning, info, status_line
from core.config import ConfigManager, get_config
from llm.model_manager import ModelManager
from llm.ollama_client import OllamaConnectionError

app = typer.Typer(help="Service lifecycle management")

# PID file locations
API_PID_FILE = Path("/tmp/aitao_api.pid")
WORKER_PID_FILE = Path("/tmp/aitao_worker.pid")


def _get_api_port() -> int:
    """Get API port from config."""
    try:
        # Change to project root to find config
        project_root = Path(__file__).parent.parent.parent.parent
        import os
        os.chdir(project_root)
        
        config = get_config()
        port = config.get("api.port", 5000)
        return port if isinstance(port, int) else int(port)
    except Exception as e:
        return 5000


def get_api_port() -> int:
    """Public helper to retrieve the API port."""
    return _get_api_port()


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
            Spinner("dots", text=f"[cyan]{name}[/cyan]..."),
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


def _start_api_server(skip_pull: bool = False) -> Tuple[bool, Optional[int]]:
    """
    Start the FastAPI server as a background process.
    
    Args:
        skip_pull: If True, skip automatic model download on startup
    
    Returns:
        (success, pid) tuple
    """
    if API_PID_FILE.exists():
        try:
            pid = int(API_PID_FILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return True, pid  # Already running
        except (ProcessLookupError, ValueError):
            API_PID_FILE.unlink(missing_ok=True)
    
    port = _get_api_port()
    
    # Start uvicorn in background
    try:
        # Use the Python from current environment
        python_path = sys.executable
        api_module = "src.api.main:app"
        
        # Build environment variables for the subprocess
        env = os.environ.copy()
        if skip_pull:
            env["AITAO_SKIP_MODEL_PULL"] = "1"
        
        # Start process detached
        process = subprocess.Popen(
            [
                python_path, "-m", "uvicorn",
                api_module,
                "--host", "0.0.0.0",
                "--port", str(port),
                "--log-level", "warning",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(src_path.parent),
            start_new_session=True,
            env=env,
        )
        
        # Save PID
        API_PID_FILE.write_text(str(process.pid))
        
        # Wait a moment and check if it started
        time.sleep(1)
        if process.poll() is None:
            return True, process.pid
        else:
            return False, None
            
    except Exception as e:
        return False, None


def _stop_api_server() -> bool:
    """Stop the API server."""
    if not API_PID_FILE.exists():
        return True
    
    try:
        pid = int(API_PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        
        # Wait for graceful shutdown
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                API_PID_FILE.unlink(missing_ok=True)
                return True
        
        # Force kill
        os.kill(pid, signal.SIGKILL)
        API_PID_FILE.unlink(missing_ok=True)
        return True
        
    except ProcessLookupError:
        API_PID_FILE.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def start_api(skip_pull: bool = False) -> Tuple[bool, Optional[int]]:
    """Public helper to start the API server."""
    return _start_api_server(skip_pull=skip_pull)


def stop_api() -> bool:
    """Public helper to stop the API server."""
    return _stop_api_server()


def _start_worker() -> Tuple[bool, Optional[int]]:
    """
    Start the background worker daemon.
    
    Returns:
        (success, pid) tuple
    """
    try:
        from indexation.worker import BackgroundWorker
        
        worker = BackgroundWorker()
        
        if worker.is_running():
            pid = worker.get_pid()
            return True, pid  # Already running
        
        # Start daemon
        if worker.start_daemon():
            time.sleep(0.5)
            pid = worker.get_pid()
            return True, pid
        else:
            return False, None
            
    except Exception as e:
        return False, None


def _stop_worker() -> bool:
    """Stop the background worker."""
    try:
        from indexation.worker import BackgroundWorker
        
        worker = BackgroundWorker()
        return worker.stop_daemon()
        
    except Exception:
        return False


def _run_initial_scan() -> Tuple[int, int]:
    """
    Run initial filesystem scan and populate queue.
    
    Returns:
        (new_files_count, modified_files_count) tuple
    """
    try:
        from indexation.scanner import FilesystemScanner
        from indexation.queue import TaskQueue
        
        scanner = FilesystemScanner()
        queue = TaskQueue()
        
        # Run scan
        result = scanner.scan(save_state=True)
        
        # Add files to queue
        added = 0
        for file_info in result.new_files + result.modified_files:
            try:
                queue.add_task(
                    file_path=file_info.path,
                    task_type="index",
                    priority="normal"
                )
                added += 1
            except Exception:
                pass  # Skip duplicates
        
        return len(result.new_files), len(result.modified_files)
        
    except Exception as e:
        return 0, 0


def _check_meilisearch_running() -> bool:
    """Check if Meilisearch is running."""
    try:
        result = subprocess.run(
            ["brew", "services", "info", "meilisearch", "--json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "started" in result.stdout.lower()
    except Exception:
        return False


@app.command()
def start(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    skip_scan: bool = typer.Option(False, "--skip-scan", help="Skip initial filesystem scan"),
    skip_pull: bool = typer.Option(False, "--skip-pull", help="Skip automatic model downloads")
):
    """
    Start all AItao services.
    
    Starts the complete AItao stack:
    1. Verify LLM models (US-021b)
    2. Download missing models if needed (unless --skip-pull)
    3. Meilisearch (full-text search engine)
    4. API server (FastAPI on port 5000)
    5. Background worker (document processing)
    6. Initial scan (unless --skip-scan)
    
    After starting, the system is ready to index and search documents.
    """
    info("🚀 Starting all AItao services...")
    console.print()
    
    all_success = True
    port = _get_api_port()
    
    # 0. Check LLM models (BEFORE Meilisearch, required by API)
    console.print("[cyan]Step 1: Verify LLM models[/cyan]")
    try:
        manager = ModelManager()
        model_status = manager.check_models()
        
        if model_status.required_missing:
            if skip_pull:
                error(f"Required models missing (and --skip-pull is set): {', '.join(model_status.required_missing)}")
                console.print("[red]Cannot start without required models[/red]")
                console.print()
                console.print("Download them with:")
                for model in model_status.required_missing:
                    console.print(f"  [cyan]ollama pull {model}:7b[/cyan]")
                console.print()
                console.print("Or run without --skip-pull to auto-download:")
                console.print("  [cyan]./aitao.sh start[/cyan]")
                raise typer.Exit(code=1)
            else:
                # Auto-download missing required models
                console.print("[yellow]Downloading missing required models...[/yellow]")
                console.print()
                
                pull_result = manager.pull_missing_models()
                
                if pull_result["required_failed"]:
                    error(f"Failed to download required models: {', '.join(pull_result['required_failed'])}")
                    console.print("[red]Cannot start without required models[/red]")
                    raise typer.Exit(code=1)
                else:
                    status_line("Models Downloaded", f"OK ({len(pull_result['required_pulled'])} models)", ok=True)
                    
                # Re-check after pulling
                model_status = manager.check_models()
        
        status_line("LLM Models", f"OK ({len(model_status.present)} present)", ok=True)
        
    except OllamaConnectionError as e:
        error(f"Cannot connect to Ollama: {str(e)}")
        console.print("[yellow]Make sure Ollama is running:[/yellow]")
        console.print("  [cyan]ollama serve[/cyan]")
        raise typer.Exit(code=1)
    except Exception as e:
        error(f"Unexpected error checking models: {str(e)}")
        raise typer.Exit(code=1)
    
    console.print()
    console.print("[cyan]Step 2: Start services[/cyan]")
    
    # 1. Start Meilisearch
    if not _run_command(
        "Meilisearch",
        ["brew", "services", "start", "meilisearch"],
        timeout=30
    ):
        all_success = False
    
    # 2. Start API server
    with Live(
        Spinner("dots", text="[cyan]API Server[/cyan]..."),
        console=console,
        transient=True,
    ):
        api_ok, api_pid = _start_api_server(skip_pull=skip_pull)
    
    if api_ok:
        status_line("API Server", f"OK (port {port}, PID {api_pid})", ok=True)
    else:
        status_line("API Server", "Failed to start", ok=False)
        all_success = False
    
    # 3. Start Worker daemon
    with Live(
        Spinner("dots", text="[cyan]Worker Daemon[/cyan]..."),
        console=console,
        transient=True,
    ):
        worker_ok, worker_pid = _start_worker()
    
    if worker_ok:
        status_line("Worker Daemon", f"OK (PID {worker_pid})", ok=True)
    else:
        status_line("Worker Daemon", "Failed to start", ok=False)
        all_success = False
    
    # 4. Run initial scan (unless skipped)
    if not skip_scan and all_success:
        console.print()
        info("📂 Running initial filesystem scan...")
        
        with Live(
            Spinner("dots", text="[cyan]Scanning documents[/cyan]..."),
            console=console,
            transient=True,
        ):
            new_count, modified_count = _run_initial_scan()
        
        total = new_count + modified_count
        if total > 0:
            status_line("Initial Scan", f"Found {new_count} new, {modified_count} modified files", ok=True)
            info(f"📋 {total} files added to queue for indexing")
        else:
            status_line("Initial Scan", "No new files found", ok=True)
    
    console.print()
    
    if all_success:
        success("✅ All services started successfully!")
        console.print()
        info("📖 API docs: http://localhost:{}/docs".format(port))
        info("🔍 Health:   http://localhost:{}/api/health".format(port))
        info("📊 Status:   ./aitao.sh status")
    else:
        warning("⚠️  Some services failed to start. Check above for details.")
        raise typer.Exit(1)


@app.command()
def stop(verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")):
    """
    Stop all AItao services.
    
    Gracefully stops:
    1. Background worker (finish current task)
    2. API server
    3. Meilisearch
    
    Services will be gracefully shut down with proper cleanup.
    """
    info("🛑 Stopping all AItao services...")
    console.print()
    
    all_success = True
    
    # 1. Stop Worker first (let it finish current task)
    with Live(
        Spinner("dots", text="[cyan]Worker Daemon[/cyan]..."),
        console=console,
        transient=True,
    ):
        worker_ok = _stop_worker()
    
    if worker_ok:
        status_line("Worker Daemon", "Stopped", ok=True)
    else:
        status_line("Worker Daemon", "Failed to stop", ok=False)
        all_success = False
    
    # 2. Stop API server
    with Live(
        Spinner("dots", text="[cyan]API Server[/cyan]..."),
        console=console,
        transient=True,
    ):
        api_ok = _stop_api_server()
    
    if api_ok:
        status_line("API Server", "Stopped", ok=True)
    else:
        status_line("API Server", "Failed to stop", ok=False)
        all_success = False
    
    # 3. Stop Meilisearch
    if not _run_command(
        "Meilisearch",
        ["brew", "services", "stop", "meilisearch"],
        timeout=30
    ):
        all_success = False
    
    console.print()
    
    if all_success:
        success("✅ All services stopped")
    else:
        warning("⚠️  Some services failed to stop. Check above for details.")
        raise typer.Exit(1)


@app.command()
def restart(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    skip_scan: bool = typer.Option(False, "--skip-scan", help="Skip initial filesystem scan")
):
    """
    Restart all AItao services.
    
    Equivalent to:
    1. Stop all services
    2. Wait for cleanup
    3. Start all services
    
    Useful after configuration changes.
    """
    info("🔄 Restarting all AItao services...")
    console.print()
    
    # Stop services
    try:
        stop(verbose=verbose)
    except typer.Exit:
        pass  # Ignore exit code from stop
    except Exception as e:
        warning(f"Error stopping services: {e}")
    
    # Wait for services to fully stop
    console.print()
    info("⏳ Waiting for services to fully stop...")
    time.sleep(3)
    console.print()
    
    # Start services
    try:
        start(verbose=verbose, skip_scan=skip_scan)
    except Exception as e:
        error(f"Error restarting services: {e}")
        raise typer.Exit(1)


@app.command()
def status():
    """
    Show status of all AItao services.
    
    Displays running state, PIDs, and ports for all managed services.
    """
    from rich.table import Table
    
    info("📊 AItao Service Status")
    console.print()
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Service", style="white")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")
    
    # Check Meilisearch
    ms_running = _check_meilisearch_running()
    table.add_row(
        "Meilisearch",
        "[green]● Running[/green]" if ms_running else "[red]● Stopped[/red]",
        "brew services" if ms_running else ""
    )
    
    # Check API
    api_running = False
    api_pid = None
    if API_PID_FILE.exists():
        try:
            api_pid = int(API_PID_FILE.read_text().strip())
            os.kill(api_pid, 0)
            api_running = True
        except (ProcessLookupError, ValueError):
            pass
    
    port = _get_api_port()
    table.add_row(
        "API Server",
        "[green]● Running[/green]" if api_running else "[red]● Stopped[/red]",
        f"PID {api_pid}, port {port}" if api_running else ""
    )
    
    # Check Worker
    worker_running = False
    worker_pid = None
    if WORKER_PID_FILE.exists():
        try:
            worker_pid = int(WORKER_PID_FILE.read_text().strip())
            os.kill(worker_pid, 0)
            worker_running = True
        except (ProcessLookupError, ValueError):
            pass
    
    table.add_row(
        "Worker Daemon",
        "[green]● Running[/green]" if worker_running else "[red]● Stopped[/red]",
        f"PID {worker_pid}" if worker_running else ""
    )
    
    console.print(table)
    console.print()
    
    # Summary
    all_running = ms_running and api_running and worker_running
    if all_running:
        success("✅ All services running")
    elif ms_running or api_running or worker_running:
        warning("⚠️  Some services not running")
    else:
        error("❌ All services stopped")


# Register in main app (will be done in main.py)
