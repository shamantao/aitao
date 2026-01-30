"""
CLI: Model Management Commands (US-021b).

Provides subcommands under `./aitao.sh models`:
- status: Show configured vs installed models
- pull: Download missing models (future: US-021c)
- add: Add a model to config (future)
- remove: Remove a model from config (future)

Status reporting includes:
- Configured models (from config.yaml)
- Installed models (from Ollama)
- Present: configured AND installed
- Missing: configured BUT not installed
- Extra: installed BUT not configured

Design principles:
- AC-003: Use structured logging (logger, not print)
- Rich tables for user-friendly output
- Color-coded status (green=ok, red=error, yellow=warning)
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.logger import get_logger
from core.config import get_config
from llm.model_manager import ModelManager
from llm.ollama_client import OllamaConnectionError

logger = get_logger(__name__)
console = Console()


app = typer.Typer(
    help="Model management commands",
    short_help="Manage LLM models",
    no_args_is_help=True,
)


def _get_model_manager() -> Optional[ModelManager]:
    """
    Create and return ModelManager.
    
    Returns None if Ollama is unreachable (with error message).
    """
    try:
        return ModelManager()
    except OllamaConnectionError as e:
        console.print(
            f"[red]ERROR: Cannot connect to Ollama[/red]\n"
            f"{str(e)}\n\n"
            f"Make sure Ollama is running:\n"
            f"  brew services start ollama\n"
            f"  OR: ollama serve",
            file=sys.stderr
        )
        return None


@app.command()
def status():
    """
    Show status of configured and installed models.
    
    Displays:
    - Configured: Models in config.yaml
    - Installed: Models available in Ollama
    - Present: Both configured AND installed (✓)
    - Missing: Configured but not installed (✗)
    - Extra: Installed but not configured
    
    Exit codes:
    - 0: All required models present
    - 1: Required models missing
    """
    manager = _get_model_manager()
    if not manager:
        raise typer.Exit(code=1)
    
    logger.info("Checking model status...")
    console.print()
    
    try:
        model_status = manager.check_models()
    except OllamaConnectionError as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Get configured models for details
    configured = manager._get_configured_models()
    configured_by_name = {m.name: m for m in configured}
    
    # ========================================================================
    # PRESENT MODELS
    # ========================================================================
    if model_status.present:
        table = Table(title="[green]✓ Present Models[/green]", show_header=True)
        table.add_column("Model", style="cyan")
        table.add_column("Required", style="magenta")
        table.add_column("Size", style="yellow")
        table.add_column("Roles", style="green")
        
        for model_name in sorted(model_status.present):
            info = manager.get_model_info(f"{model_name}:8b")  # Try with :8b tag
            if not info:
                # Try without tag
                for m in configured:
                    if manager._parse_model_name(m.name) == model_name:
                        info = m
                        break
            
            required = "✓" if info and info.required else "○"
            size = f"{info.size_gb}G" if info and info.size_gb else "?"
            roles = ", ".join([r.value for r in info.roles]) if info else ""
            
            table.add_row(model_name, required, size, roles)
        
        console.print(table)
        console.print()
    
    # ========================================================================
    # MISSING MODELS (REQUIRED)
    # ========================================================================
    if model_status.required_missing:
        table = Table(
            title="[red]✗ Required Models MISSING[/red]",
            show_header=True,
            border_style="red"
        )
        table.add_column("Model", style="red")
        table.add_column("Size", style="yellow")
        table.add_column("Action", style="cyan")
        
        for model_name in sorted(model_status.required_missing):
            info = None
            for m in configured:
                if manager._parse_model_name(m.name) == model_name:
                    info = m
                    break
            
            size = f"{info.size_gb}G" if info and info.size_gb else "?"
            action = f"ollama pull {model_name}:7b"
            
            table.add_row(model_name, size, action)
        
        console.print(table)
        console.print()
        
        msg = (
            "[red]ERROR[/red]: The following [bold]required[/bold] models are missing:\n"
            f"{', '.join(model_status.required_missing)}\n\n"
            "Cannot start AItao without these models.\n\n"
            "To download them manually:\n"
        )
        for model in model_status.required_missing:
            msg += f"  ollama pull {model}:7b\n"
        
        console.print(Panel(msg, border_style="red"))
        logger.error("Required models missing", metadata={"models": model_status.required_missing})
        raise typer.Exit(code=1)
    
    # ========================================================================
    # MISSING MODELS (OPTIONAL)
    # ========================================================================
    if model_status.missing:
        table = Table(title="[yellow]⚠ Optional Models Missing[/yellow]", show_header=True)
        table.add_column("Model", style="yellow")
        table.add_column("Size", style="yellow")
        table.add_column("Roles", style="green")
        
        for model_name in sorted(model_status.missing):
            info = None
            for m in configured:
                if manager._parse_model_name(m.name) == model_name:
                    info = m
                    break
            
            size = f"{info.size_gb}G" if info and info.size_gb else "?"
            roles = ", ".join([r.value for r in info.roles]) if info else ""
            
            table.add_row(model_name, size, roles)
        
        console.print(table)
        console.print(
            "[yellow]💡 Tip:[/yellow] Download these with "
            "`./aitao.sh models pull` (future)"
        )
        console.print()
    
    # ========================================================================
    # EXTRA MODELS
    # ========================================================================
    if model_status.extra:
        console.print(
            "[dim]ℹ Extra models installed (not in config):[/dim] "
            f"{', '.join(sorted(model_status.extra))}"
        )
        console.print()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    summary = (
        f"[cyan]Configured:[/cyan] {len(model_status.present) + len(model_status.missing)}\n"
        f"[green]Present:[/green] {len(model_status.present)}\n"
        f"[yellow]Missing:[/yellow] {len(model_status.missing)}\n"
        f"[blue]Extra:[/blue] {len(model_status.extra)}"
    )
    console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="cyan"))
    
    logger.info(
        "Model status checked",
        metadata={
            "present": len(model_status.present),
            "missing": len(model_status.missing),
            "extra": len(model_status.extra),
            "required_missing": len(model_status.required_missing)
        }
    )
    
    # Exit with 0 if all OK
    raise typer.Exit(code=0)


@app.command()
def pull():
    """
    Download missing configured models from Ollama hub.
    
    This is a future feature (US-021c).
    Currently, use: ollama pull <model>
    """
    console.print("[yellow]Feature not yet implemented (US-021c)[/yellow]")
    console.print()
    console.print("For now, download models manually:")
    console.print()
    
    manager = _get_model_manager()
    if not manager:
        raise typer.Exit(code=1)
    
    try:
        model_status = manager.check_models()
    except OllamaConnectionError as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if model_status.missing:
        for model in sorted(model_status.missing):
            console.print(f"  [cyan]ollama pull {model}:7b[/cyan]")
    else:
        console.print("  [green]All configured models are already installed![/green]")
    
    console.print()
    console.print("[dim]This command will auto-download in a future sprint.[/dim]")


@app.command()
def add(model_name: str):
    """
    Add a model to config.yaml (future: US-021e).
    
    Example:
      ./aitao.sh models add llama3.1:8b
    """
    console.print("[yellow]Feature not yet implemented (US-021e)[/yellow]")
    console.print(f"To add '{model_name}' manually:")
    console.print()
    console.print("1. Edit config/config.yaml")
    console.print("2. Add to 'llm.models' section:")
    console.print(f"   - name: {model_name}")
    console.print("     required: false")
    console.print("3. Save and reload")


@app.command()
def remove(model_name: str):
    """
    Remove a model from config.yaml (future: US-021e).
    
    Example:
      ./aitao.sh models remove llama3.1:8b
    """
    console.print("[yellow]Feature not yet implemented (US-021e)[/yellow]")
    console.print(f"To remove '{model_name}' manually:")
    console.print()
    console.print("1. Edit config/config.yaml")
    console.print("2. Remove from 'llm.models' section:")
    console.print(f"   (delete the entry for {model_name})")
    console.print("3. Optionally, remove from Ollama:")
    console.print(f"   ollama rm {model_name}")


if __name__ == "__main__":
    app()
