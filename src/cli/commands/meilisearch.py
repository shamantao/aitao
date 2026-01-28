"""
Meilisearch management commands.

Commands:
- aitao ms status   Show Meilisearch status
- aitao ms start    Start Meilisearch server
- aitao ms stop     Stop Meilisearch server
- aitao ms upgrade  Upgrade Meilisearch (brew)
- aitao ms rebuild  Rebuild the search index
"""

import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional

import typer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils import (
    console, success, error, warning, info,
    print_header, status_line, confirm, create_progress
)


app = typer.Typer(help="Meilisearch management")


@app.command("status")
def ms_status():
    """Show Meilisearch server status."""
    print_header("Meilisearch Status")
    
    try:
        from search.meilisearch_client import MeilisearchClient
        client = MeilisearchClient()
        
        if client.is_healthy():
            status_line("Server", "Running")
            status_line("Version", client.get_version())
            status_line("URL", client.host)
            
            stats = client.get_stats()
            status_line("Index", client.index_name)
            status_line("Documents", str(stats.get("total_documents", 0)))
            
            if stats.get("is_indexing"):
                warning("Server is currently indexing...")
        else:
            status_line("Server", "Not responding", ok=False)
            _show_start_help()
            
    except Exception as e:
        status_line("Server", f"Error: {e}", ok=False)
        _show_start_help()


def _show_start_help():
    """Show help for starting Meilisearch."""
    console.print()
    info("To start Meilisearch:")
    console.print("  [dim]brew services start meilisearch[/dim]")
    console.print("  [dim]or: meilisearch --http-addr localhost:7700[/dim]")


@app.command("start")
def ms_start():
    """Start Meilisearch server via brew services."""
    info("Starting Meilisearch...")
    
    if not shutil.which("brew"):
        error("Homebrew not found. Please start Meilisearch manually.")
        raise typer.Exit(1)
    
    result = subprocess.run(
        ["brew", "services", "start", "meilisearch"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        success("Meilisearch started")
        console.print(f"  {result.stdout.strip()}")
    else:
        error(f"Failed to start: {result.stderr}")
        raise typer.Exit(1)


@app.command("stop")
def ms_stop():
    """Stop Meilisearch server via brew services."""
    info("Stopping Meilisearch...")
    
    if not shutil.which("brew"):
        error("Homebrew not found. Please stop Meilisearch manually.")
        raise typer.Exit(1)
    
    result = subprocess.run(
        ["brew", "services", "stop", "meilisearch"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        success("Meilisearch stopped")
    else:
        error(f"Failed to stop: {result.stderr}")
        raise typer.Exit(1)


@app.command("restart")
def ms_restart():
    """Restart Meilisearch server."""
    info("Restarting Meilisearch...")
    
    if not shutil.which("brew"):
        error("Homebrew not found.")
        raise typer.Exit(1)
    
    result = subprocess.run(
        ["brew", "services", "restart", "meilisearch"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        success("Meilisearch restarted")
    else:
        error(f"Failed to restart: {result.stderr}")
        raise typer.Exit(1)


@app.command("upgrade")
def ms_upgrade(
    skip_confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Upgrade Meilisearch to latest version.
    
    This will:
    1. Stop the service
    2. Export current data (optional)
    3. Upgrade via brew
    4. Start the service
    5. Verify health
    """
    print_header("Meilisearch Upgrade")
    
    if not shutil.which("brew"):
        error("Homebrew not found. Please upgrade manually.")
        raise typer.Exit(1)
    
    # Show current version
    try:
        from search.meilisearch_client import MeilisearchClient
        client = MeilisearchClient()
        if client.is_healthy():
            current_version = client.get_version()
            info(f"Current version: {current_version}")
        else:
            warning("Meilisearch not running")
            current_version = "unknown"
    except Exception:
        current_version = "unknown"
    
    # Check for updates
    info("Checking for updates...")
    result = subprocess.run(
        ["brew", "outdated", "meilisearch"],
        capture_output=True, text=True
    )
    
    if "meilisearch" not in result.stdout:
        success("Meilisearch is already up to date!")
        raise typer.Exit(0)
    
    console.print(f"  Available: {result.stdout.strip()}")
    
    if not skip_confirm:
        console.print()
        warning("⚠️  Upgrading may require reindexing if there's a major version change.")
        if not confirm("Proceed with upgrade?"):
            info("Upgrade cancelled")
            raise typer.Exit(0)
    
    # Perform upgrade
    with create_progress() as progress:
        task = progress.add_task("Upgrading Meilisearch...", total=4)
        
        # Step 1: Stop service
        progress.update(task, description="Stopping service...")
        subprocess.run(["brew", "services", "stop", "meilisearch"], 
                      capture_output=True)
        progress.update(task, advance=1)
        
        # Step 2: Upgrade
        progress.update(task, description="Upgrading via brew...")
        result = subprocess.run(
            ["brew", "upgrade", "meilisearch"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            error(f"Upgrade failed: {result.stderr}")
            raise typer.Exit(1)
        progress.update(task, advance=1)
        
        # Step 3: Start service
        progress.update(task, description="Starting service...")
        subprocess.run(["brew", "services", "start", "meilisearch"],
                      capture_output=True)
        progress.update(task, advance=1)
        
        # Step 4: Wait and verify
        progress.update(task, description="Verifying health...")
        import time
        time.sleep(2)  # Give it time to start
        progress.update(task, advance=1)
    
    # Final check
    console.print()
    try:
        client = MeilisearchClient()
        if client.is_healthy():
            new_version = client.get_version()
            success(f"Upgrade complete! Version: {new_version}")
        else:
            warning("Server started but not responding yet. Check: brew services list")
    except Exception as e:
        warning(f"Could not verify: {e}")


@app.command("rebuild")
def ms_rebuild(
    skip_confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Rebuild the search index from scratch."""
    print_header("Rebuild Meilisearch Index")
    
    try:
        from search.meilisearch_client import MeilisearchClient
        client = MeilisearchClient()
        
        if not client.is_healthy():
            error("Meilisearch is not running")
            raise typer.Exit(1)
        
        stats = client.get_stats()
        doc_count = stats.get("total_documents", 0)
        
        if doc_count > 0:
            warning(f"This will delete {doc_count} documents from the index.")
            if not skip_confirm and not confirm("Proceed?"):
                info("Cancelled")
                raise typer.Exit(0)
        
        # Clear the index
        info("Clearing index...")
        client.clear_index()
        success("Index cleared. Reindex with: aitao index <path>")
        
    except Exception as e:
        error(f"Failed: {e}")
        raise typer.Exit(1)
