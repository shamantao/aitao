"""
LanceDB (Vector Database) management commands.

Commands:
- aitao db status   Show database status
- aitao db stats    Show detailed statistics
- aitao db clear    Clear the database
- aitao db rebuild  Rebuild vector embeddings
"""

import sys
from pathlib import Path
from typing import Optional

import typer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils import (
    console, success, error, warning, info,
    print_header, status_line, confirm, create_table
)
from core.registry import StatsKeys


app = typer.Typer(help="LanceDB (vector database) management")


@app.command("status")
def db_status():
    """Show LanceDB status."""
    print_header("LanceDB Status")
    
    try:
        from search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        
        stats = client.get_stats()
        
        status_line("Database path", str(client.db_path))
        status_line("Table", client.table_name)
        status_line("Documents", str(stats.get(StatsKeys.TOTAL_DOCUMENTS, 0)))
        
        if stats.get(StatsKeys.EMBEDDING_DIMENSION):
            status_line("Embedding dimension", str(stats[StatsKeys.EMBEDDING_DIMENSION]))
        
        if stats.get(StatsKeys.TOTAL_DOCUMENTS, 0) > 0:
            status_line("Disk size", _format_size(stats.get("size_bytes", 0)))
        
    except Exception as e:
        error(f"Error: {e}")
        raise typer.Exit(1)


@app.command("stats")
def db_stats():
    """Show detailed database statistics."""
    print_header("LanceDB Statistics")
    
    try:
        from search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        
        stats = client.get_stats()
        
        if stats.get(StatsKeys.TOTAL_DOCUMENTS, 0) == 0:
            info("Database is empty")
            return
        
        # Basic info
        console.print("[bold]Basic Info[/bold]")
        status_line("Total documents", str(stats.get(StatsKeys.TOTAL_DOCUMENTS, 0)))
        status_line("Embedding dimension", str(stats.get(StatsKeys.EMBEDDING_DIMENSION, 0)))
        
        console.print()
        
        # Table info
        table = create_table("Schema")
        table.add_column("Field", style="cyan")
        table.add_column("Type")
        
        # Get schema from LanceDB
        if hasattr(client, '_table') and client._table:
            schema = client._table.schema
            for field in schema:
                table.add_row(field.name, str(field.type))
            console.print(table)
        
    except Exception as e:
        error(f"Error: {e}")
        raise typer.Exit(1)


@app.command("clear")
def db_clear(
    skip_confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all documents from the database."""
    print_header("Clear LanceDB")
    
    try:
        from search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        
        stats = client.get_stats()
        doc_count = stats.get(StatsKeys.TOTAL_DOCUMENTS, 0)
        
        if doc_count == 0:
            info("Database is already empty")
            return
        
        warning(f"This will delete {doc_count} documents and their embeddings.")
        
        if not skip_confirm and not confirm("Proceed?"):
            info("Cancelled")
            raise typer.Exit(0)
        
        # Clear
        info("Clearing database...")
        client.clear()
        success("Database cleared")
        
    except Exception as e:
        error(f"Error: {e}")
        raise typer.Exit(1)


@app.command("search")
def db_search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of results"),
):
    """Perform a semantic search in the database."""
    try:
        from search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        
        stats = client.get_stats()
        if stats.get(StatsKeys.TOTAL_DOCUMENTS, 0) == 0:
            info("Database is empty. Index some documents first.")
            return
        
        info(f"Searching for: {query}")
        console.print()
        
        results = client.search(query, limit=limit)
        
        if not results:
            info("No results found")
            return
        
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            title = result.get("title", "Untitled")
            path = result.get("path", "")
            
            # Score as percentage similarity
            similarity = (1 - score) * 100 if score < 1 else 0
            
            console.print(f"[bold]{i}.[/bold] {title}")
            console.print(f"   [dim]{path}[/dim]")
            console.print(f"   [green]Similarity: {similarity:.1f}%[/green]")
            console.print()
            
    except Exception as e:
        error(f"Search error: {e}")
        raise typer.Exit(1)


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
