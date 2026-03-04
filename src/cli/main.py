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

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli.utils import console
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
from cli.commands import api as api_cmd

# Import version
try:
    from core.version import get_version
except ImportError:
    def get_version() -> str:
        return "unknown"


# Create main app
app = typer.Typer(
    name="aitao",
    help="AItao V2 - Document Search & Translation Engine",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
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
app.add_typer(api_cmd.app, name="api", help="API server management")


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


@app.callback()
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


def run():
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    run()
