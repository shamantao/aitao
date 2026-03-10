"""
Scan commands - Filesystem scanning for document discovery.

Commands:
- aitao scan          Scan configured paths for new/modified files
- aitao scan paths    Show configured scan paths
- aitao scan status   Show scanner state and stats
- aitao scan clear    Clear scanner state (force full rescan)
"""

import sys
from pathlib import Path
from typing import Optional, List

import typer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils import (
    console, success, error, warning, info,
    print_header, status_line, confirm, create_table, spinner,
    get_config_path
)


app = typer.Typer(help="Filesystem scanning")


@app.command("run")
def scan_run(
    paths: Optional[List[str]] = typer.Argument(
        None, help="Specific paths to scan (default: use config)"
    ),
    no_hash: bool = typer.Option(
        False, "--no-hash", help="Skip SHA256 hash computation (faster)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Scan but don't update state"
    ),
):
    """
    Scan filesystem for new and modified documents.
    
    Scans the paths configured in config.toml (indexing.include_paths)
    and identifies files that need to be indexed.
    """
    print_header("Filesystem Scan")
    
    try:
        from indexation.scanner import FilesystemScanner
        
        config_path = str(get_config_path())
        
        with spinner("Initializing scanner..."):
            scanner = FilesystemScanner(config_path=config_path)
        
        # Show what we're scanning
        if paths:
            info(f"Scanning {len(paths)} specified path(s)")
        else:
            info(f"Scanning {len(scanner.include_paths)} configured path(s)")
            for p in scanner.include_paths:
                console.print(f"  [dim]{p}[/dim]")
        
        console.print()
        
        # Run the scan
        with spinner("Scanning filesystem..."):
            result = scanner.scan(
                paths=paths,
                compute_hashes=not no_hash,
                save_state=not dry_run
            )
        
        # Results
        console.print()
        if result.has_changes:
            if result.new_files:
                success(f"New files: {len(result.new_files)}")
                for f in result.new_files[:10]:  # Show first 10
                    console.print(f"  [green]+[/green] {Path(f.path).name}")
                if len(result.new_files) > 10:
                    console.print(f"  [dim]... and {len(result.new_files) - 10} more[/dim]")
            
            if result.modified_files:
                warning(f"Modified files: {len(result.modified_files)}")
                for f in result.modified_files[:10]:
                    console.print(f"  [yellow]~[/yellow] {Path(f.path).name}")
                if len(result.modified_files) > 10:
                    console.print(f"  [dim]... and {len(result.modified_files) - 10} more[/dim]")
            
            if result.deleted_paths:
                error(f"Deleted files: {len(result.deleted_paths)}")
                for p in result.deleted_paths[:10]:
                    console.print(f"  [red]-[/red] {Path(p).name}")
                if len(result.deleted_paths) > 10:
                    console.print(f"  [dim]... and {len(result.deleted_paths) - 10} more[/dim]")
        else:
            success("No changes detected")
        
        console.print()
        
        # Summary
        table = create_table("Scan Summary", [("Metric", "right"), ("Value", "left")])
        table.add_row("Files scanned", str(result.total_scanned))
        table.add_row("Files skipped", str(result.total_skipped))
        table.add_row("Duration", f"{result.scan_duration_seconds:.2f}s")
        if dry_run:
            table.add_row("Mode", "[yellow]Dry run (state not saved)[/yellow]")
        console.print(table)
        
    except FileNotFoundError as e:
        error(f"Configuration not found: {e}")
        raise typer.Exit(1)
    except Exception as e:
        error(f"Scan failed: {e}")
        raise typer.Exit(1)


@app.command("paths")
def scan_paths():
    """Show configured scan paths."""
    print_header("Scan Paths")
    
    try:
        from indexation.scanner import FilesystemScanner
        
        config_path = str(get_config_path())
        scanner = FilesystemScanner(config_path=config_path)
        
        console.print("[bold]Include paths:[/bold]")
        if scanner.include_paths:
            for p in scanner.include_paths:
                exists = "✓" if p.exists() else "✗"
                color = "green" if p.exists() else "red"
                console.print(f"  [{color}]{exists}[/{color}] {p}")
        else:
            warning("No include paths configured")
        
        console.print()
        console.print("[bold]Exclude directories:[/bold]")
        console.print(f"  [dim]{', '.join(sorted(scanner.exclude_dirs)[:10])}...[/dim]")
        
        console.print()
        console.print("[bold]Supported extensions:[/bold]")
        exts = sorted(scanner.supported_extensions)
        console.print(f"  [dim]{', '.join(exts[:15])}... ({len(exts)} total)[/dim]")
        
    except Exception as e:
        error(f"Error: {e}")
        raise typer.Exit(1)


@app.command("status")
def scan_status():
    """Show scanner state and statistics."""
    print_header("Scanner Status")
    
    try:
        from indexation.scanner import FilesystemScanner
        
        config_path = str(get_config_path())
        scanner = FilesystemScanner(config_path=config_path)
        
        stats = scanner.get_stats()
        
        status_line("State file", stats["state_file"])
        status_line("Tracked files", str(stats["tracked_files"]))
        status_line("Include paths", str(len(stats["include_paths"])))
        status_line("Supported extensions", str(stats["supported_extensions"]))
        
    except Exception as e:
        error(f"Error: {e}")
        raise typer.Exit(1)


@app.command("clear")
def scan_clear(
    skip_confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear scanner state (force full rescan on next run)."""
    try:
        from indexation.scanner import FilesystemScanner
        
        config_path = str(get_config_path())
        scanner = FilesystemScanner(config_path=config_path)
        
        stats = scanner.get_stats()
        tracked = stats["tracked_files"]
        
        if tracked == 0:
            info("Scanner state is already empty")
            return
        
        warning(f"This will clear state for {tracked} tracked files.")
        
        if not skip_confirm and not confirm("Proceed?"):
            info("Cancelled")
            raise typer.Exit(0)
        
        scanner.clear_state()
        success("Scanner state cleared")
        info("Next scan will treat all files as new")
        
    except Exception as e:
        error(f"Error: {e}")
        raise typer.Exit(1)
