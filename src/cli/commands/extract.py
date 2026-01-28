"""
CLI commands for text extraction.

Provides commands to extract and preview text from documents.
Useful for testing extraction before full indexing.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from cli.utils import status_line, spinner

console = Console()
app = typer.Typer(help="Extract and preview text from documents")


@app.command("file")
def extract_file(
    file_path: str = typer.Argument(..., help="Path to file to extract"),
    preview: int = typer.Option(500, "--preview", "-p", help="Characters to preview (0=full)"),
    metadata: bool = typer.Option(False, "--metadata", "-m", help="Show metadata only"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Extract text from a single file.
    
    Examples:
        ./aitao.sh extract file document.pdf
        ./aitao.sh extract file document.docx --preview 1000
        ./aitao.sh extract file document.pdf --metadata
        ./aitao.sh extract file document.pdf --json
    """
    from indexation.text_extractor import TextExtractor
    
    path = Path(file_path)
    
    # Resolve relative paths
    if not path.is_absolute():
        import os
        orig_pwd = os.environ.get("AITAO_ORIG_PWD", os.getcwd())
        path = Path(orig_pwd) / path
    
    if not path.exists():
        console.print(f"[red]❌ File not found: {path}[/red]")
        raise typer.Exit(1)
    
    extractor = TextExtractor()
    
    if not extractor.can_extract(path):
        console.print(f"[red]❌ Unsupported file type: {path.suffix}[/red]")
        console.print(f"[dim]Supported: {', '.join(sorted(extractor.get_supported_extensions()))}[/dim]")
        raise typer.Exit(1)
    
    with spinner(f"Extracting text from {path.name}..."):
        result = extractor.extract(path)
    
    if json_output:
        import json
        output = {
            "success": result.success,
            "file": str(path),
            "metadata": result.metadata,
        }
        if not metadata:
            output["text"] = result.text if preview == 0 else result.text[:preview]
        if result.error:
            output["error"] = result.error
        console.print_json(json.dumps(output))
        return
    
    if not result.success:
        console.print(f"[red]❌ Extraction failed: {result.error}[/red]")
        raise typer.Exit(1)
    
    # Show metadata
    console.print()
    console.print(Panel(f"[bold]{path.name}[/bold]", title="Extraction Result"))
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    
    for key, value in result.metadata.items():
        if key not in ("file_path", "file_name"):
            table.add_row(key, str(value))
    
    console.print(table)
    
    if not metadata:
        console.print()
        text = result.text
        if preview > 0 and len(text) > preview:
            text = text[:preview] + f"\n\n[dim]... ({len(result.text) - preview} more characters)[/dim]"
        
        console.print(Panel(text, title="Extracted Text", border_style="green"))


@app.command("batch")
def extract_batch(
    directory: str = typer.Argument(..., help="Directory to scan"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r/-R", help="Scan recursively"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum files to process"),
):
    """
    Extract text from multiple files in a directory.
    
    Shows a summary of extraction results.
    
    Examples:
        ./aitao.sh extract batch ~/Documents
        ./aitao.sh extract batch ~/Documents --limit 50
        ./aitao.sh extract batch ~/Documents --no-recursive
    """
    from indexation.text_extractor import TextExtractor
    
    path = Path(directory)
    
    if not path.is_absolute():
        import os
        orig_pwd = os.environ.get("AITAO_ORIG_PWD", os.getcwd())
        path = Path(orig_pwd) / path
    
    if not path.exists() or not path.is_dir():
        console.print(f"[red]❌ Directory not found: {path}[/red]")
        raise typer.Exit(1)
    
    extractor = TextExtractor()
    supported = extractor.get_supported_extensions()
    
    # Find files
    if recursive:
        files = [f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in supported]
    else:
        files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in supported]
    
    if not files:
        console.print(f"[yellow]⚠ No supported files found in {path}[/yellow]")
        return
    
    files = files[:limit]
    console.print(f"[bold]Processing {len(files)} files...[/bold]\n")
    
    # Process files
    results = []
    success_count = 0
    total_words = 0
    
    for file in files:
        result = extractor.extract(file)
        results.append((file, result))
        if result.success:
            success_count += 1
            total_words += result.word_count
    
    # Show results table
    table = Table(title=f"Extraction Results ({success_count}/{len(files)} successful)")
    table.add_column("File", style="cyan", max_width=40)
    table.add_column("Type", style="blue")
    table.add_column("Words", justify="right")
    table.add_column("Language", style="green")
    table.add_column("Status")
    
    for file, result in results:
        if result.success:
            table.add_row(
                file.name,
                result.metadata.get("file_type", "?"),
                str(result.word_count),
                result.language or "-",
                "[green]✓[/green]"
            )
        else:
            table.add_row(
                file.name,
                file.suffix,
                "-",
                "-",
                f"[red]✗ {result.error[:30]}...[/red]" if len(result.error or "") > 30 else f"[red]✗ {result.error}[/red]"
            )
    
    console.print(table)
    console.print()
    console.print(f"[bold]Total words extracted:[/bold] {total_words:,}")


@app.command("types")
def show_types():
    """
    Show all supported file types for extraction.
    
    Example:
        ./aitao.sh extract types
    """
    from indexation.text_extractor import TextExtractor, EXTRACTORS
    
    # Get extractors list from class
    try:
        from indexation.text_extractor import (
            PDFExtractor, DOCXExtractor, JSONExtractor,
            CodeExtractor, PlainTextExtractor
        )
        extractors = [
            ("PDF", PDFExtractor),
            ("DOCX", DOCXExtractor),
            ("JSON", JSONExtractor),
            ("Code", CodeExtractor),
            ("Plain Text", PlainTextExtractor),
        ]
    except ImportError:
        extractor = TextExtractor()
        console.print(f"[bold]Supported extensions:[/bold]")
        extensions = sorted(extractor.get_supported_extensions())
        console.print(", ".join(extensions))
        return
    
    console.print(Panel("[bold]Text Extraction - Supported File Types[/bold]"))
    console.print()
    
    for name, ext_class in extractors:
        extensions = sorted(ext_class.SUPPORTED_EXTENSIONS)
        console.print(f"[bold cyan]{name}[/bold cyan]")
        console.print(f"  {', '.join(extensions)}")
        console.print()


@app.command("test")
def test_extraction():
    """
    Run a quick test of the extraction system.
    
    Example:
        ./aitao.sh extract test
    """
    from indexation.text_extractor import TextExtractor
    import tempfile
    
    console.print(Panel("[bold]Testing Text Extraction[/bold]"))
    console.print()
    
    extractor = TextExtractor()
    
    # Test 1: Plain text
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello, this is a test document for AItao text extraction.\nIt has multiple lines.")
        txt_path = Path(f.name)
    
    try:
        result = extractor.extract(txt_path)
        status_line("Plain text (.txt)", "OK" if result.success else f"FAIL: {result.error}", ok=result.success)
        if result.success:
            status_line("  Word count", str(result.word_count))
            status_line("  Language", result.language or "unknown")
    finally:
        txt_path.unlink()
    
    # Test 2: JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"name": "test", "value": 42}')
        json_path = Path(f.name)
    
    try:
        result = extractor.extract(json_path)
        status_line("JSON (.json)", "OK" if result.success else f"FAIL: {result.error}", ok=result.success)
    finally:
        json_path.unlink()
    
    # Test 3: Python code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('def hello():\n    """Say hello."""\n    print("Hello, World!")\n')
        py_path = Path(f.name)
    
    try:
        result = extractor.extract(py_path)
        status_line("Python code (.py)", "OK" if result.success else f"FAIL: {result.error}", ok=result.success)
    finally:
        py_path.unlink()
    
    # Test 4: Check PDF support
    try:
        import pypdf
        status_line("PDF support (pypdf)", "Available", ok=True)
    except ImportError:
        status_line("PDF support (pypdf)", "Not installed", ok=False)
    
    # Test 5: Check DOCX support
    try:
        import docx
        status_line("DOCX support (python-docx)", "Available", ok=True)
    except ImportError:
        status_line("DOCX support (python-docx)", "Not installed", ok=False)
    
    # Test 6: Check langdetect
    try:
        import langdetect
        status_line("Language detection (langdetect)", "Available", ok=True)
    except ImportError:
        status_line("Language detection (langdetect)", "Not installed", ok=False)
    
    console.print()
    console.print(f"[bold]Supported extensions:[/bold] {len(extractor.get_supported_extensions())}")
