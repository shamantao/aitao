"""
CLI commands for document indexing.

Provides commands to index documents into LanceDB and Meilisearch.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from cli.utils import status_line, spinner
from core.registry import StatsKeys

console = Console()
app = typer.Typer(help="Index documents into search databases")


@app.command("file")
def index_file(
    file_path: str = typer.Argument(..., help="Path to file to index"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-index even if exists"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Index a single file into LanceDB and Meilisearch.
    
    Examples:
        ./aitao.sh index file document.pdf
        ./aitao.sh index file document.pdf --force
        ./aitao.sh index file document.pdf --json
    """
    from indexation.indexer import DocumentIndexer
    
    path = Path(file_path)
    
    # Resolve relative paths
    if not path.is_absolute():
        import os
        orig_pwd = os.environ.get("AITAO_ORIG_PWD", os.getcwd())
        path = Path(orig_pwd) / path
    
    if not path.exists():
        console.print(f"[red]❌ File not found: {path}[/red]")
        raise typer.Exit(1)
    
    try:
        indexer = DocumentIndexer()
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize indexer: {e}[/red]")
        raise typer.Exit(1)
    
    with spinner(f"Indexing {path.name}..."):
        result = indexer.index_file(path, force=force)
    
    if json_output:
        import json
        output = {
            "path": result.path,
            "doc_id": result.doc_id,
            "success": result.success,
            "lancedb_indexed": result.lancedb_indexed,
            "meilisearch_indexed": result.meilisearch_indexed,
            "word_count": result.word_count,
            "language": result.language,
            "extraction_time_ms": round(result.extraction_time_ms, 2),
            "indexing_time_ms": round(result.indexing_time_ms, 2),
            "total_time_ms": round(result.total_time_ms, 2),
        }
        if result.error:
            output["error"] = result.error
        console.print_json(json.dumps(output))
        return
    
    # Display result
    console.print()
    
    if result.success:
        if result.error and "Already indexed" in result.error:
            console.print(Panel(f"[yellow]⏭ Skipped: {path.name}[/yellow]\n{result.error}", 
                               title="Already Indexed"))
        else:
            console.print(Panel(f"[green]✓ Indexed: {path.name}[/green]", title="Success"))
            
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Key", style="cyan")
            table.add_column("Value")
            
            table.add_row("Document ID", result.doc_id[:16] + "...")
            table.add_row("LanceDB", "[green]✓[/green]" if result.lancedb_indexed else "[red]✗[/red]")
            table.add_row("Meilisearch", "[green]✓[/green]" if result.meilisearch_indexed else "[red]✗[/red]")
            table.add_row("Word count", str(result.word_count))
            table.add_row("Language", result.language or "unknown")
            table.add_row("Extraction time", f"{result.extraction_time_ms:.1f}ms")
            table.add_row("Indexing time", f"{result.indexing_time_ms:.1f}ms")
            
            console.print(table)
    else:
        console.print(Panel(f"[red]✗ Failed: {path.name}[/red]\n{result.error}", title="Error"))
        raise typer.Exit(1)


@app.command("batch")
def index_batch(
    directory: str = typer.Argument(..., help="Directory to scan and index"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r/-R", 
                                    help="Scan subdirectories"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-index existing documents"),
    limit: int = typer.Option(0, "--limit", "-l", help="Maximum files to process (0=unlimited)"),
):
    """
    Index all supported files in a directory.
    
    Examples:
        ./aitao.sh index batch ~/Documents
        ./aitao.sh index batch ~/Documents --no-recursive
        ./aitao.sh index batch ~/Documents --force --limit 100
    """
    from indexation.indexer import DocumentIndexer
    from indexation.text_extractor import TextExtractor
    
    path = Path(directory)
    
    if not path.is_absolute():
        import os
        orig_pwd = os.environ.get("AITAO_ORIG_PWD", os.getcwd())
        path = Path(orig_pwd) / path
    
    if not path.exists() or not path.is_dir():
        console.print(f"[red]❌ Directory not found: {path}[/red]")
        raise typer.Exit(1)
    
    # Find files first
    extractor = TextExtractor()
    supported = extractor.get_supported_extensions()
    
    console.print(f"[bold]Scanning {path}...[/bold]")
    
    if recursive:
        files = [f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in supported]
    else:
        files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in supported]
    
    if limit > 0:
        files = files[:limit]
    
    if not files:
        console.print(f"[yellow]⚠ No supported files found[/yellow]")
        return
    
    console.print(f"Found [bold]{len(files)}[/bold] files to index\n")
    
    try:
        indexer = DocumentIndexer()
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize indexer: {e}[/red]")
        raise typer.Exit(1)
    
    # Index with progress bar
    successful = 0
    failed = 0
    skipped = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing...", total=len(files))
        
        for file in files:
            result = indexer.index_file(file, force=force)
            
            if result.success:
                if result.error and "Already indexed" in result.error:
                    skipped += 1
                else:
                    successful += 1
            else:
                failed += 1
            
            progress.update(task, advance=1, description=f"Indexing {file.name[:30]}...")
    
    # Summary
    console.print()
    console.print(Panel(
        f"[green]✓ Indexed: {successful}[/green]\n"
        f"[yellow]⏭ Skipped: {skipped}[/yellow]\n"
        f"[red]✗ Failed: {failed}[/red]",
        title="Batch Indexing Complete"
    ))


@app.command("status")
def index_status():
    """
    Show indexing statistics from both databases.
    
    Example:
        ./aitao.sh index status
    """
    from indexation.indexer import DocumentIndexer
    
    console.print(Panel("[bold]Indexing Statistics[/bold]"))
    console.print()
    
    try:
        indexer = DocumentIndexer()
        stats = indexer.get_stats()
    except Exception as e:
        console.print(f"[red]❌ Failed to get stats: {e}[/red]")
        raise typer.Exit(1)
    
    # LanceDB stats
    console.print("[bold cyan]LanceDB (Semantic Search)[/bold cyan]")
    if stats.get("lancedb"):
        ldb = stats["lancedb"]
        if "error" in ldb:
            status_line("Status", f"Error: {ldb['error']}", ok=False)
        else:
            # Use StatsKeys for consistent key access
            doc_count = ldb.get(StatsKeys.TOTAL_DOCUMENTS, 0)
            status_line("Documents", str(doc_count))
            status_line("Table", ldb.get(StatsKeys.TABLE_NAME, "unknown"))
            status_line("Embedding dimension", str(ldb.get(StatsKeys.EMBEDDING_DIMENSION, "unknown")))
            if ldb.get(StatsKeys.DB_PATH):
                status_line("Database path", ldb.get(StatsKeys.DB_PATH))
    else:
        status_line("Status", "Not available", ok=False)
    
    console.print()
    
    # Meilisearch stats
    console.print("[bold cyan]Meilisearch (Full-text Search)[/bold cyan]")
    if stats.get("meilisearch"):
        ms = stats["meilisearch"]
        if "error" in ms:
            status_line("Status", f"Error: {ms['error']}", ok=False)
        else:
            # Use StatsKeys for consistent key access
            doc_count = ms.get(StatsKeys.TOTAL_DOCUMENTS, 0)
            status_line("Documents", str(doc_count))
            status_line("Index", ms.get(StatsKeys.INDEX_NAME, "unknown"))
            server = ms.get(StatsKeys.HOST, "unknown")
            status_line("Server", server)
    else:
        status_line("Status", "Not available", ok=False)


@app.command("delete")
def delete_document(
    file_path: str = typer.Argument(..., help="Path of document to delete from indexes"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Delete a document from both search indexes.
    
    Example:
        ./aitao.sh index delete ~/Documents/old_file.pdf
        ./aitao.sh index delete ~/Documents/old_file.pdf --yes
    """
    from indexation.indexer import DocumentIndexer
    
    path = Path(file_path)
    
    if not path.is_absolute():
        import os
        orig_pwd = os.environ.get("AITAO_ORIG_PWD", os.getcwd())
        path = Path(orig_pwd) / path
    
    if not confirm:
        console.print(f"[yellow]This will delete the document from both search indexes:[/yellow]")
        console.print(f"  {path}")
        console.print()
        if not typer.confirm("Are you sure?"):
            console.print("[dim]Cancelled[/dim]")
            return
    
    try:
        indexer = DocumentIndexer()
        success, message = indexer.delete_document(path)
        
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ Delete failed: {message}[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("test")
def test_indexing():
    """
    Run a quick test of the indexing pipeline.
    
    Example:
        ./aitao.sh index test
    """
    from indexation.indexer import DocumentIndexer
    import tempfile
    
    console.print(Panel("[bold]Testing Document Indexing Pipeline[/bold]"))
    console.print()
    
    # Test 1: Check components
    console.print("[bold]1. Component Check[/bold]")
    
    try:
        indexer = DocumentIndexer()
        status_line("DocumentIndexer", "OK")
    except Exception as e:
        status_line("DocumentIndexer", f"FAIL: {e}", ok=False)
        raise typer.Exit(1)
    
    # Check LanceDB
    try:
        if indexer.lancedb:
            stats = indexer.lancedb.get_stats()
            status_line("LanceDB", f"OK ({stats.get('document_count', 0)} docs)")
        else:
            status_line("LanceDB", "Not available", ok=False)
    except Exception as e:
        status_line("LanceDB", f"FAIL: {e}", ok=False)
    
    # Check Meilisearch
    try:
        if indexer.meilisearch:
            if indexer.meilisearch.is_healthy():
                stats = indexer.meilisearch.get_stats()
                status_line("Meilisearch", f"OK ({stats.get('document_count', 0)} docs)")
            else:
                status_line("Meilisearch", "Not healthy", ok=False)
        else:
            status_line("Meilisearch", "Not available", ok=False)
    except Exception as e:
        status_line("Meilisearch", f"FAIL: {e}", ok=False)
    
    console.print()
    
    # Test 2: Index a test file
    console.print("[bold]2. Test Indexing[/bold]")
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test document for AItao indexing pipeline. "
                "It contains enough text for language detection to work properly. "
                "The document should be indexed in both LanceDB and Meilisearch.")
        test_path = Path(f.name)
    
    try:
        result = indexer.index_file(test_path, force=True)
        
        if result.success:
            status_line("Test file indexed", "OK")
            status_line("  LanceDB", "✓" if result.lancedb_indexed else "✗", ok=result.lancedb_indexed)
            status_line("  Meilisearch", "✓" if result.meilisearch_indexed else "✗", ok=result.meilisearch_indexed)
            status_line("  Extraction time", f"{result.extraction_time_ms:.1f}ms")
            status_line("  Indexing time", f"{result.indexing_time_ms:.1f}ms")
        else:
            status_line("Test file indexed", f"FAIL: {result.error}", ok=False)
        
        # Clean up: delete test document from indexes
        indexer.delete_document(test_path)
    finally:
        test_path.unlink(missing_ok=True)
    
    console.print()
    console.print("[bold green]Pipeline test complete![/bold green]")
