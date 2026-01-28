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


@app.callback()
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output"),
):
    """
    AItao V2 - Document Search & Translation Engine
    
    Local-first, privacy-focused document management.
    """
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        ctx.obj = {"debug": True}


def run():
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    run()
