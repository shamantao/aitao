"""
CLI commands for Background Worker management.

This module provides commands to control the document processing worker:
- Start/stop the worker daemon
- Check worker status
- Run a single task manually
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel

# Import utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils import (
    get_config_path,
    success,
    error,
    warning,
    info,
    spinner,
    status_line
)
# Heavy import — loaded lazily inside functions to keep CLI startup fast
# from indexation.worker import BackgroundWorker

console = Console()
app = typer.Typer(
    help=(
        "Contrôle du worker de traitement en arrière-plan.\n\n"
        "[bold cyan]Exemples[/bold cyan]\n\n"
        "  Démarrer le worker seul (sans Meilisearch) :\n"
        "    [green]./aitao.sh worker start[/green]\n\n"
        "  Voir l'état et le PID :\n"
        "    [green]./aitao.sh worker status[/green]\n\n"
        "  Arrêter le worker :\n"
        "    [green]./aitao.sh worker stop[/green]\n\n"
        "  Voir les logs du worker :\n"
        "    [green]./aitao.sh worker logs[/green]\n\n"
        "  Traiter une seule tâche (test) :\n"
        "    [green]./aitao.sh worker run-once[/green]\n\n"
        "[dim]Note : ./aitao.sh start démarre le worker ET Meilisearch ensemble.[/dim]"
    ),
    rich_markup_mode="rich",
)


def get_worker():
    """Get configured BackgroundWorker instance."""
    from indexation.worker import BackgroundWorker  # lazy import
    config_path = get_config_path()
    return BackgroundWorker(config_path=config_path)


@app.command()
def status():
    """Show worker status."""
    try:
        worker = get_worker()
        
        is_running = worker.is_running()
        pid = worker.get_pid()
        
        if is_running:
            lines = [
                "[bold green]● Running[/bold green]",
                "",
                f"[bold]PID:[/bold] {pid}",
                f"[bold]PID file:[/bold] {worker.pid_file}",
            ]
            
            # Get queue stats
            queue_stats = worker.queue.get_stats()
            pending = queue_stats['pending']
            poll_interval = worker.worker_config.poll_interval
            
            lines.append("")
            lines.append("[bold]Queue:[/bold]")
            lines.append(f"  Pending: {pending}")
            lines.append(f"  Processing: {queue_stats['processing']}")
            lines.append(f"  Completed: {queue_stats['completed']}")
            lines.append(f"  Failed: {queue_stats['failed']}")
            
            # ETA calculation
            if pending > 0:
                eta_seconds = pending * poll_interval
                if eta_seconds < 60:
                    eta_str = f"~{eta_seconds}s"
                elif eta_seconds < 3600:
                    eta_str = f"~{eta_seconds // 60}min"
                else:
                    hours = eta_seconds // 3600
                    mins = (eta_seconds % 3600) // 60
                    eta_str = f"~{hours}h{mins:02d}min"
                lines.append("")
                lines.append(f"[bold]ETA:[/bold] {eta_str} ({poll_interval}s/task)")
            
            console.print(Panel(
                "\n".join(lines),
                title="⚙️ Worker Status",
                border_style="green"
            ))
        else:
            lines = [
                "[bold red]● Stopped[/bold red]",
                "",
                f"[bold]PID file:[/bold] {worker.pid_file}",
            ]
            
            # Get queue stats
            queue_stats = worker.queue.get_stats()
            if queue_stats['pending'] > 0:
                lines.append("")
                lines.append(f"[yellow]⚠ {queue_stats['pending']} pending tasks waiting[/yellow]")
            
            console.print(Panel(
                "\n".join(lines),
                title="⚙️ Worker Status",
                border_style="red"
            ))
        
    except Exception as e:
        error(f"Failed to get worker status: {e}")
        raise typer.Exit(1)


@app.command()
def start(
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground (blocking)")
):
    """Start the background worker."""
    try:
        worker = get_worker()
        
        if worker.is_running():
            warning(f"Worker already running (PID: {worker.get_pid()})")
            return
        
        if foreground:
            info("Starting worker in foreground (Ctrl+C to stop)...")
            console.print()
            worker.run()
        else:
            with spinner("Starting worker daemon..."):
                result = worker.start_daemon()
            
            if result:
                success(f"Worker started (PID: {worker.get_pid()})")
            else:
                error("Failed to start worker")
                raise typer.Exit(1)
        
    except KeyboardInterrupt:
        info("Worker stopped by user")
    except typer.Exit:
        raise
    except Exception as e:
        error(f"Failed to start worker: {e}")
        raise typer.Exit(1)


@app.command()
def stop(
    force: bool = typer.Option(False, "--force", "-f", help="Force kill if not responding")
):
    """Stop the background worker."""
    try:
        worker = get_worker()
        
        if not worker.is_running():
            info("Worker not running")
            return
        
        pid = worker.get_pid()
        timeout = 5 if force else 10
        
        with spinner("Stopping worker..."):
            result = worker.stop_daemon(timeout=timeout)
        
        if result:
            success(f"Worker stopped (was PID: {pid})")
        else:
            error("Failed to stop worker")
            raise typer.Exit(1)
        
    except typer.Exit:
        raise
    except Exception as e:
        error(f"Failed to stop worker: {e}")
        raise typer.Exit(1)


@app.command()
def restart():
    """Restart the background worker."""
    try:
        worker = get_worker()
        
        if worker.is_running():
            with spinner("Stopping worker..."):
                worker.stop_daemon()
        
        import time
        time.sleep(1)
        
        with spinner("Starting worker..."):
            result = worker.start_daemon()
        
        if result:
            success(f"Worker restarted (PID: {worker.get_pid()})")
        else:
            error("Failed to restart worker")
            raise typer.Exit(1)
        
    except typer.Exit:
        raise
    except Exception as e:
        error(f"Failed to restart worker: {e}")
        raise typer.Exit(1)


@app.command("run-once")
def run_once():
    """Process one task from the queue (for testing)."""
    try:
        worker = get_worker()
        
        queue_stats = worker.queue.get_stats()
        if queue_stats['pending'] == 0:
            info("No pending tasks in queue")
            return
        
        with spinner("Processing one task..."):
            result = worker.run_once()
        
        if result:
            success("Task processed successfully")
        else:
            warning("No task processed (queue empty or CPU high)")
        
    except Exception as e:
        error(f"Failed to process task: {e}")
        raise typer.Exit(1)


@app.command()
def logs(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
):
    """Show worker logs."""
    try:
        worker = get_worker()
        
        # Determine log file path
        if worker.config_manager:
            logs_dir = worker.config_manager.get("paths.logs_dir", "logs")
            log_path = Path(os.path.expandvars(logs_dir)).expanduser() / "worker.log"
        else:
            log_path = Path("logs/worker.log")
        
        import os
        if not log_path.exists():
            info(f"No log file found at {log_path}")
            return
        
        if follow:
            import subprocess
            cmd = ["tail", "-f", "-n", str(lines), str(log_path)]
            info(f"Following {log_path} (Ctrl+C to stop)")
            subprocess.run(cmd)
        else:
            import subprocess
            cmd = ["tail", "-n", str(lines), str(log_path)]
            subprocess.run(cmd)
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        error(f"Failed to show logs: {e}")
        raise typer.Exit(1)
