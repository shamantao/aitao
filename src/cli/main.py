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
from cli.commands import dashboard as dashboard_cmd
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
from cli.commands import license as license_cmd

# Import version
try:
    from core.version import get_version
except ImportError:
    def get_version() -> str:
        return "unknown"


# Create main app
app = typer.Typer(
    name="aitao",
    help=(
        "AiTao — Moteur de recherche et d'indexation documentaire local.\n\n"
        "[bold cyan]Démarrage rapide[/bold cyan]\n\n"
        "  [green]./aitao.sh start[/green]              Démarrer tous les services\n"
        "  [green]./aitao.sh dashboard[/green]           État en un coup d'œil\n"
        "  [green]./aitao.sh stop[/green]               Arrêter tous les services\n\n"
        "[bold cyan]Fichiers en échec ?[/bold cyan]\n\n"
        "  [green]./aitao.sh queue list failed[/green]   Voir quels fichiers ont échoué\n"
        "  [green]./aitao.sh queue retry[/green]         Remettre les échecs en attente\n"
        "  [green]./aitao.sh start[/green]               Relancer le traitement\n\n"
        "[bold cyan]Vectorisation incomplète (LanceDB < Meilisearch) ?[/bold cyan]\n\n"
        "  [green]./aitao.sh scan run[/green]            Re-scanner les dossiers\n"
        "  [green]./aitao.sh start[/green]               Compléter la vectorisation\n\n"
        "[bold cyan]Détail d'une erreur ?[/bold cyan]\n\n"
        "  [green]./aitao.sh queue list failed -n 100[/green]  Lister jusqu'à 100 échecs\n"
        "  [green]./aitao.sh queue info <TASK_ID>[/green]      Détail complet d'une tâche"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)

# Register command groups — help text is defined in each sub-module's typer.Typer()
app.add_typer(ms_cmd.app, name="ms")
app.add_typer(db_cmd.app, name="db")
app.add_typer(config_cmd.app, name="config")
app.add_typer(scan_cmd.app, name="scan")
app.add_typer(queue_cmd.app, name="queue")
app.add_typer(worker_cmd.app, name="worker")
app.add_typer(extract_cmd.app, name="extract")
app.add_typer(index_cmd.app, name="index")
app.add_typer(search_cmd.app, name="search")
app.add_typer(lifecycle_cmd.app, name="lifecycle")
app.add_typer(models_cmd.app, name="models")
app.add_typer(api_cmd.app, name="api")
app.add_typer(license_cmd.app, name="license")


@app.command()
def status():
    """Show AItao system status."""
    status_cmd.show_status()


@app.command()
def dashboard():
    """Show AiTao dashboard — all services, models, index and errors at a glance."""
    dashboard_cmd.show_dashboard()


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
