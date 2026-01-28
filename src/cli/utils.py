"""
CLI utility functions for consistent output formatting.

Provides helpers for:
- Colored console output
- Progress bars and spinners
- Status indicators
- Error formatting
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import print as rprint


# Shared console instance
console = Console()


def success(message: str) -> None:
    """Print success message in green."""
    console.print(f"[bold green]✓[/bold green] {message}")


def error(message: str) -> None:
    """Print error message in red."""
    console.print(f"[bold red]✗[/bold red] {message}")


def warning(message: str) -> None:
    """Print warning message in yellow."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def info(message: str) -> None:
    """Print info message in blue."""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def status_line(label: str, value: str, ok: bool = True) -> None:
    """Print a status line with label and colored value."""
    color = "green" if ok else "red"
    console.print(f"  {label}: [{color}]{value}[/{color}]")


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print a styled header."""
    text = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        text += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(text, expand=False))


def create_table(title: str, columns: list[tuple[str, str]]) -> Table:
    """
    Create a styled table.
    
    Args:
        title: Table title
        columns: List of (name, justify) tuples
    
    Returns:
        Rich Table object
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for name, justify in columns:
        table.add_column(name, justify=justify)
    return table


def create_progress() -> Progress:
    """Create a styled progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )


def confirm(message: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"{message}{suffix} ").strip().lower()
    
    if not response:
        return default
    return response in ("y", "yes", "oui", "o")
