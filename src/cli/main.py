"""
AItao CLI main entry point.

This module defines the root Typer application and registers
all command groups. Run with:

    python -m aitao.cli --help
    python -m aitao.cli status
    python -m aitao.cli ms upgrade
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli.utils import console, print_header, info
from cli.commands import status as status_cmd
from cli.commands import meilisearch as ms_cmd
from cli.commands import database as db_cmd
from cli.commands import config as config_cmd
from cli.commands import scan as scan_cmd
from cli.commands import queue as queue_cmd
from cli.commands import worker as worker_cmd
from cli.commands import extract as extract_cmd
from cli.commands import index as index_cmd
from cli.commands import search as search_cmd
from cli.commands import lifecycle as lifecycle_cmd
from cli.commands import models as models_cmd

# Import version
try:
    from core.version import get_version
except ImportError:
    def get_version() -> str:
        return "unknown"


def _show_detailed_help():
    """Show detailed help with all commands and subcommands."""
    from rich.table import Table
    from rich.panel import Panel
    
    ver = get_version()
    
    # Header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]☯️ AItao V2[/bold cyan] [dim]v{ver}[/dim]\n"
        "[dim]Document Search & Translation Engine[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    # Main commands
    console.print("[bold]Commands:[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="green")
    table.add_column("Description")
    
    table.add_row("status", "Show system health (services, config, databases)")
    table.add_row("version", "Show version")
    table.add_row("test", "Run unit tests")
    console.print(table)
    console.print()
    
    # Meilisearch commands
    console.print("[bold]Meilisearch (ms):[/bold]  [dim]Full-text search engine[/dim]")
    ms_table = Table(show_header=False, box=None, padding=(0, 2))
    ms_table.add_column("Command", style="yellow")
    ms_table.add_column("Description")
    
    ms_table.add_row("ms status", "Check if server is running")
    ms_table.add_row("ms start", "Start server (brew services)")
    ms_table.add_row("ms stop", "Stop server")
    ms_table.add_row("ms restart", "Restart server")
    ms_table.add_row("ms upgrade", "Upgrade to latest version")
    ms_table.add_row("ms rebuild", "Clear and rebuild index")
    console.print(ms_table)
    console.print()
    
    # Database commands
    console.print("[bold]LanceDB (db):[/bold]  [dim]Vector embeddings database[/dim]")
    db_table = Table(show_header=False, box=None, padding=(0, 2))
    db_table.add_column("Command", style="blue")
    db_table.add_column("Description")
    
    db_table.add_row("db status", "Show database status")
    db_table.add_row("db stats", "Detailed statistics")
    db_table.add_row("db clear", "Clear all embeddings")
    db_table.add_row("db search \"query\"", "Semantic search test")
    console.print(db_table)
    console.print()
    
    # Config commands
    console.print("[bold]Configuration (config):[/bold]")
    cfg_table = Table(show_header=False, box=None, padding=(0, 2))
    cfg_table.add_column("Command", style="magenta")
    cfg_table.add_column("Description")
    
    cfg_table.add_row("config show", "Display current config")
    cfg_table.add_row("config show search", "Show specific section")
    cfg_table.add_row("config validate", "Validate configuration")
    cfg_table.add_row("config edit", "Open in editor")
    console.print(cfg_table)
    console.print()
    
    # Scan commands
    console.print("[bold]Filesystem Scan (scan):[/bold]  [dim]Document discovery[/dim]")
    scan_table = Table(show_header=False, box=None, padding=(0, 2))
    scan_table.add_column("Command", style="cyan")
    scan_table.add_column("Description")
    
    scan_table.add_row("scan run", "Scan for new/modified files")
    scan_table.add_row("scan run --dry-run", "Preview without saving state")
    scan_table.add_row("scan paths", "Show configured scan paths")
    scan_table.add_row("scan status", "Show scanner state")
    scan_table.add_row("scan clear", "Reset state (force full rescan)")
    console.print(scan_table)
    console.print()
    
    # Queue commands
    console.print("[bold]Task Queue (queue):[/bold]  [dim]Document processing queue[/dim]")
    queue_table = Table(show_header=False, box=None, padding=(0, 2))
    queue_table.add_column("Command", style="green")
    queue_table.add_column("Description")
    
    queue_table.add_row("queue status", "Show queue statistics")
    queue_table.add_row("queue list", "List tasks in queue")
    queue_table.add_row("queue list --pending", "Show only pending tasks")
    queue_table.add_row("queue add <file>", "Add file to queue")
    queue_table.add_row("queue retry", "Retry failed tasks")
    queue_table.add_row("queue clear", "Clear completed tasks")
    console.print(queue_table)
    console.print()
    
    # Worker commands
    console.print("[bold]Background Worker (worker):[/bold]  [dim]Document processing daemon[/dim]")
    worker_table = Table(show_header=False, box=None, padding=(0, 2))
    worker_table.add_column("Command", style="magenta")
    worker_table.add_column("Description")
    
    worker_table.add_row("worker status", "Show worker status")
    worker_table.add_row("worker start", "Start worker daemon")
    worker_table.add_row("worker start -f", "Run in foreground")
    worker_table.add_row("worker stop", "Stop worker daemon")
    worker_table.add_row("worker restart", "Restart worker")
    worker_table.add_row("worker run-once", "Process one task")
    console.print(worker_table)
    console.print()
    
    # Search commands
    console.print("[bold]Hybrid Search (search):[/bold]  [dim]Search across documents[/dim]")
    search_table = Table(show_header=False, box=None, padding=(0, 2))
    search_table.add_column("Command", style="cyan")
    search_table.add_column("Description")
    
    search_table.add_row("search \"query\"", "Quick hybrid search")
    search_table.add_row("search run \"query\"", "Full search with options")
    search_table.add_row("search run -m semantic", "Semantic-only search")
    search_table.add_row("search run -m fulltext", "Full-text only search")
    search_table.add_row("search test", "Run search diagnostics")
    search_table.add_row("search modes", "Explain search modes")
    console.print(search_table)
    console.print()
    
    # Models commands
    console.print("[bold]LLM Models (models):[/bold]  [dim]Model management[/dim]")
    models_table = Table(show_header=False, box=None, padding=(0, 2))
    models_table.add_column("Command", style="magenta")
    models_table.add_column("Description")
    
    models_table.add_row("models status", "Show configured vs installed models")
    models_table.add_row("models pull", "Download missing models (future)")
    models_table.add_row("models add <name>", "Add model to config (future)")
    models_table.add_row("models remove <name>", "Remove model from config (future)")
    console.print(models_table)
    console.print()
    console.print("[bold]Options:[/bold]")
    console.print("  [dim]-d, --debug[/dim]    Enable verbose logging")
    console.print("  [dim]-q, --quiet[/dim]    Suppress all logs")
    console.print("  [dim]--help[/dim]         Show this help")
    console.print()
    
    # Examples
    console.print("[bold]Examples:[/bold]")
    console.print("  [dim]./aitao.sh status[/dim]              # Quick health check")
    console.print("  [dim]./aitao.sh scan run[/dim]            # Scan for new documents")
    console.print("  [dim]./aitao.sh ms upgrade[/dim]          # Update Meilisearch")
    console.print("  [dim]./aitao.sh db search \"tao\"[/dim]     # Test semantic search")
    console.print("  [dim]./aitao.sh --debug status[/dim]      # Verbose output")
    console.print()


# Create main app
app = typer.Typer(
    name="aitao",
    help="AItao V2 - Document Search & Translation Engine",
    no_args_is_help=False,  # We handle this ourselves
    rich_markup_mode="rich",
    add_completion=True,
    invoke_without_command=True,  # Allow callback to run without command
)

# Register command groups
app.add_typer(ms_cmd.app, name="ms", help="Meilisearch management")
app.add_typer(db_cmd.app, name="db", help="LanceDB vector database")
app.add_typer(config_cmd.app, name="config", help="Configuration management")
app.add_typer(scan_cmd.app, name="scan", help="Filesystem scanning")
app.add_typer(queue_cmd.app, name="queue", help="Task queue management")
app.add_typer(worker_cmd.app, name="worker", help="Background worker control")
app.add_typer(extract_cmd.app, name="extract", help="Text extraction from documents")
app.add_typer(index_cmd.app, name="index", help="Document indexing pipeline")
app.add_typer(search_cmd.app, name="search", help="Hybrid document search")
app.add_typer(lifecycle_cmd.app, name="lifecycle", help="Service lifecycle (start/stop/restart)")
app.add_typer(models_cmd.app, name="models", help="LLM model management")


@app.command()
def status():
    """Show AItao system status."""
    status_cmd.show_status()


@app.command()
def version():
    """Show AItao version."""
    ver = get_version()
    console.print(f"[bold cyan]aitao[/bold cyan] {ver}")


@app.command()
def test(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run unit tests."""
    import subprocess
    
    cmd = ["pytest", "tests/unit/", "-v" if verbose else "-q"]
    result = subprocess.run(cmd, cwd=src_path.parent)
    raise typer.Exit(result.returncode)


@app.command()
def start(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Start all AItao services (Meilisearch, Worker).
    
    Shortcut for: ./aitao.sh lifecycle start
    """
    lifecycle_cmd.start(verbose=verbose)


@app.command()
def stop(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Stop all AItao services (Worker, Meilisearch).
    
    Shortcut for: ./aitao.sh lifecycle stop
    """
    lifecycle_cmd.stop(verbose=verbose)


@app.command()
def restart(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Restart all AItao services.
    
    Shortcut for: ./aitao.sh lifecycle restart
    """
    lifecycle_cmd.restart(verbose=verbose)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress log output"),
):
    """
    AItao V2 - Document Search & Translation Engine
    
    Local-first, privacy-focused document management.
    """
    import os
    
    # Set quiet mode by default in CLI (cleaner output with spinners)
    if not debug:
        os.environ["AITAO_QUIET"] = "1"
    
    if quiet:
        os.environ["AITAO_QUIET"] = "1"
    
    if debug:
        import logging
        os.environ.pop("AITAO_QUIET", None)  # Unset quiet in debug mode
        os.environ["AITAO_LOG_LEVEL"] = "DEBUG"
        logging.basicConfig(level=logging.DEBUG)
        ctx.obj = {"debug": True}
    
    # If no command provided, show detailed help
    if ctx.invoked_subcommand is None:
        _show_detailed_help()


def run():
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    run()
