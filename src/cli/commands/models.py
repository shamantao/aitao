"""
CLI: Model Management Commands (US-021b).

Provides subcommands under `./aitao.sh models`:
- status: Show configured vs installed models
- pull: Download missing models (future: US-021c)
- add: Add a model to config (future)
- remove: Remove a model from config (future)

Status reporting includes:
- Configured models (from config.toml)
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
from cli.commands._models_helpers import (
    validate_model_name,
    get_model_from_config,
    load_config_yaml,
    save_config_yaml,
    prompt_model_metadata,
    check_model_dependencies,
)

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
    - Configured: Models in config.toml
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
    
    Downloads all missing required models (blocking if any missing) and
    optional models (non-blocking if any missing).
    
    Uses: ollama pull <model>
    """
    manager = _get_model_manager()
    if not manager:
        raise typer.Exit(code=1)
    
    # Check what's missing
    try:
        model_status = manager.check_models()
    except OllamaConnectionError as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not model_status.missing:
        console.print("[green]✓ All configured models are already installed![/green]")
        raise typer.Exit(code=0)
    
    # Show what we're about to download
    console.print()
    if model_status.required_missing:
        console.print(f"[red]Required models missing ({len(model_status.required_missing)}):[/red]")
        for model in sorted(model_status.required_missing):
            console.print(f"  ✗ {model}")
    
    if model_status.missing and not model_status.required_missing:
        # These are optional missing models
        console.print(f"[yellow]Optional models missing ({len(model_status.missing)}):[/yellow]")
        for model in sorted(model_status.missing):
            console.print(f"  ○ {model}")
    
    console.print()
    console.print("[cyan]Downloading models...[/cyan]")
    console.print()
    
    # Run the pull operation
    try:
        result = manager.pull_missing_models()
    except FileNotFoundError as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        console.print()
        console.print("Please install Ollama from: https://ollama.ai", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Report results
    console.print()
    
    # Required models
    if result["required_pulled"]:
        console.print("[green]✓ Successfully downloaded required models:[/green]")
        for model in sorted(result["required_pulled"]):
            console.print(f"  ✓ {model}")
    
    if result["required_failed"]:
        console.print("[red]✗ Failed to download required models:[/red]")
        for model in sorted(result["required_failed"]):
            console.print(f"  ✗ {model}")
        console.print()
        console.print("[red]ERROR: Cannot start without required models![/red]", file=sys.stderr)
        console.print()
        console.print("Try downloading manually:", file=sys.stderr)
        for model in sorted(result["required_failed"]):
            console.print(f"  ollama pull {model}:7b", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Optional models
    if result["optional_pulled"]:
        console.print("[green]✓ Successfully downloaded optional models:[/green]")
        for model in sorted(result["optional_pulled"]):
            console.print(f"  ○ {model}")
    
    if result["optional_failed"]:
        console.print("[yellow]⚠ Failed to download optional models:[/yellow]")
        for model in sorted(result["optional_failed"]):
            console.print(f"  ○ {model}")
    
    # Summary
    console.print()
    elapsed = result.get("total_time_seconds", 0)
    summary = (
        f"[cyan]Downloaded:[/cyan] {len(result['required_pulled']) + len(result['optional_pulled'])} models\n"
        f"[yellow]Failed:[/yellow] {len(result['required_failed']) + len(result['optional_failed'])} models\n"
        f"[dim]Time:[/dim] {elapsed:.1f} seconds"
    )
    console.print(Panel(summary, title="[bold]Pull Summary[/bold]", border_style="cyan"))
    
    logger.info(
        "Pull command complete",
        metadata={
            "success": result["success"],
            "required_pulled": len(result["required_pulled"]),
            "required_failed": len(result["required_failed"]),
            "optional_pulled": len(result["optional_pulled"]),
            "optional_failed": len(result["optional_failed"]),
        }
    )
    
    raise typer.Exit(code=0 if result["success"] else 1)


@app.command()
def add(
    model_name: str = typer.Argument(..., help="Model name (e.g., llama3.1:8b)"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Model role (rag, code, extraction, chat)"),
    required: bool = typer.Option(False, "--required", help="Mark as required for startup"),
    no_pull: bool = typer.Option(False, "--no-pull", help="Add to config but don't pull")
):
    """
    Add a model to config.toml and optionally download it.
    
    Examples:
      ./aitao.sh models add llama3.1:8b
      ./aitao.sh models add qwen3-vl:latest --role rag
      ./aitao.sh models add mistral:7b --required --no-pull
    """
    import subprocess
    
    console.print()
    logger.info("Adding model to config", metadata={"model": model_name})
    
    # Validate model name
    try:
        normalized_name = validate_model_name(model_name)
    except typer.BadParameter as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Check if already in config
    if get_model_from_config(normalized_name):
        console.print(
            f"[yellow]⚠ Model '{normalized_name}' is already configured[/yellow]"
        )
        raise typer.Exit(code=1)
    
    # Prompt for metadata if not provided via options
    if role or required:
        roles_list = [r.strip() for r in role.split(",")] if role else ["rag"]
        metadata = {"role": roles_list, "required": required}
    else:
        metadata = prompt_model_metadata()
    
    # Load current config
    try:
        config = load_config_yaml()
    except FileNotFoundError as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Ensure llm.models section exists
    if "llm" not in config:
        config["llm"] = {}
    if "models" not in config["llm"]:
        config["llm"]["models"] = []
    
    # Add model entry
    new_model = {
        "name": normalized_name,
        "required": metadata.get("required", False),
        "roles": metadata.get("role", ["rag"]),
        "description": "Added via CLI"
    }
    config["llm"]["models"].append(new_model)
    
    # Save config
    try:
        save_config_yaml(config)
    except Exception as e:
        console.print(f"[red]ERROR: Cannot write config.toml[/red]\n{str(e)}")
        logger.error("Failed to save config", metadata={"error": str(e)})
        raise typer.Exit(code=1)
    
    console.print(f"[green]✓ Added {normalized_name} to config.toml[/green]")
    console.print(f"  Roles: {', '.join(metadata.get('role', ['rag']))}")
    console.print(f"  Required: {'Yes' if metadata.get('required') else 'No'}")
    console.print()
    
    # Pull model unless --no-pull
    if not no_pull:
        console.print("[cyan]Downloading model from Ollama hub...[/cyan]")
        
        manager = _get_model_manager()
        if not manager:
            console.print(
                "[yellow]⚠ Model added to config but could not download[/yellow]\n"
                f"Ollama is not running. To download manually:\n"
                f"  ollama pull {normalized_name}"
            )
            raise typer.Exit(code=0)
        
        try:
            result = subprocess.run(
                ["ollama", "pull", normalized_name],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Downloaded {normalized_name}[/green]")
            else:
                console.print(f"[yellow]⚠ Download failed: {result.stderr}[/yellow]")
                logger.warning(
                    "Model download failed",
                    metadata={"model": normalized_name, "stderr": result.stderr}
                )
        except FileNotFoundError:
            console.print(
                "[red]ERROR: ollama command not found[/red]\n"
                "Please install Ollama: https://ollama.ai"
            )
            raise typer.Exit(code=1)
        except subprocess.TimeoutExpired:
            console.print("[red]ERROR: Download timed out (10 min limit)[/red]")
            raise typer.Exit(code=1)
    
    console.print()
    status_msg = "✓ Ready to use" if not no_pull else "✓ Added to config (download later)"
    console.print(f"[green]{status_msg}[/green]")
    console.print("[dim]Next: ./aitao.sh models status[/dim]")
    
    logger.info(
        "Model added successfully",
        metadata={
            "model": normalized_name,
            "roles": metadata.get("role"),
            "required": metadata.get("required"),
            "pulled": not no_pull
        }
    )


@app.command()
def remove(
    model_name: str = typer.Argument(..., help="Model name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    delete_ollama: bool = typer.Option(False, "--delete-ollama", help="Also remove from Ollama")
):
    """
    Remove a model from config.toml (optionally from Ollama too).
    
    Examples:
      ./aitao.sh models remove llama3.1:8b
      ./aitao.sh models remove mistral:7b --force
      ./aitao.sh models remove qwen:latest --delete-ollama
    """
    console.print()
    logger.info("Removing model from config", metadata={"model": model_name})
    
    # Validate model name
    try:
        normalized_name = validate_model_name(model_name)
    except typer.BadParameter as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Find model in config
    model = get_model_from_config(normalized_name)
    if not model:
        console.print(f"[yellow]⚠ Model '{normalized_name}' not found in config[/yellow]")
        raise typer.Exit(code=1)
    
    # Check dependencies
    deps = check_model_dependencies(normalized_name)
    
    # Show warnings
    if deps["is_required"]:
        console.print(
            "[red]⚠ WARNING: This model is marked REQUIRED[/red]\n"
            "[dim]Removing it may break startup checks[/dim]"
        )
    
    if deps["only_model_for_roles"]:
        console.print(
            f"[red]⚠ WARNING: This is the ONLY model for roles:[/red]\n"
            f"[yellow]  {', '.join(deps['only_model_for_roles'])}[/yellow]\n"
            f"[dim]Removing it may break functionality[/dim]"
        )
    
    console.print()
    
    # Prompt for confirmation unless --force
    if not force and (deps["has_warnings"] or delete_ollama):
        if not typer.confirm("Continue?"):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(code=0)
    
    # Load and modify config
    try:
        config = load_config_yaml()
    except FileNotFoundError as e:
        console.print(f"[red]ERROR: {str(e)}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Remove from models list
    base_name = normalized_name.split(":")[0]
    original_count = len(config.get("llm", {}).get("models", []))
    
    config["llm"]["models"] = [
        m for m in config["llm"]["models"]
        if m.get("name", "").split(":")[0] != base_name
    ]
    
    if len(config["llm"]["models"]) == original_count:
        console.print("[red]ERROR: Could not find model to remove[/red]")
        raise typer.Exit(code=1)
    
    # Save config
    try:
        save_config_yaml(config)
    except Exception as e:
        console.print(f"[red]ERROR: Cannot write config.toml[/red]\n{str(e)}")
        raise typer.Exit(code=1)
    
    console.print(f"[green]✓ Removed {normalized_name} from config.toml[/green]")
    
    # Delete from Ollama if requested
    if delete_ollama:
        manager = _get_model_manager()
        if not manager:
            console.print(
                "[yellow]⚠ Could not connect to Ollama to delete model[/yellow]\n"
                f"[dim]To delete manually: ollama rm {normalized_name}[/dim]"
            )
            raise typer.Exit(code=0)
        
        try:
            if manager.ollama_client.delete_model(normalized_name):
                console.print("[green]✓ Removed from Ollama[/green]")
            else:
                console.print("[yellow]⚠ Model not found in Ollama (may already be deleted)[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not delete from Ollama: {str(e)}[/yellow]")
            logger.warning(
                "Failed to delete model from Ollama",
                metadata={"model": normalized_name, "error": str(e)}
            )
    
    console.print()
    console.print("[green]✓ Model removed[/green]")
    console.print("[dim]Next: ./aitao.sh models status[/dim]")
    
    logger.info(
        "Model removed successfully",
        metadata={"model": normalized_name, "deleted_from_ollama": delete_ollama}
    )


# ============================================================================
# US-029: Template Check and Fix Commands
# ============================================================================

@app.command()
def check():
    """
    Check all installed models for template issues.
    
    Detects models with broken or incomplete ChatML templates
    that may cause incoherent responses or hallucinations.
    
    Exit codes:
    - 0: All templates OK
    - 1: Broken templates found (run 'models fix' to repair)
    """
    import subprocess
    
    console.print()
    console.print("[cyan]🔍 Checking model templates...[/cyan]")
    console.print()
    
    # Call the fix script with --check
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "fix_ollama_templates.py"
    
    if not script_path.exists():
        console.print(f"[red]ERROR: Script not found: {script_path}[/red]")
        raise typer.Exit(code=1)
    
    result = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        capture_output=False,
    )
    
    raise typer.Exit(code=result.returncode)


@app.command()
def fix(
    model: Optional[str] = typer.Argument(
        None,
        help="Specific model to fix (optional, fixes all if not specified)"
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Run validation test after fixing"
    ),
):
    """
    Fix broken model templates.
    
    Repairs models that have incomplete ChatML templates, which cause
    incoherent responses or hallucinations. This recreates the model
    with the correct template from config/modelfiles/.
    
    Examples:
        ./aitao.sh models fix                    # Fix all broken models
        ./aitao.sh models fix qwen2.5-coder-local  # Fix specific model
        ./aitao.sh models fix --no-validate     # Skip validation
    
    Exit codes:
    - 0: All fixes successful
    - 1: Some fixes failed
    """
    import subprocess
    
    console.print()
    console.print("[cyan]🔧 Fixing model templates...[/cyan]")
    console.print()
    
    # Build command
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "fix_ollama_templates.py"
    
    if not script_path.exists():
        console.print(f"[red]ERROR: Script not found: {script_path}[/red]")
        raise typer.Exit(code=1)
    
    cmd = [sys.executable, str(script_path), "--fix"]
    if model:
        cmd.extend(["--model", model])
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        console.print()
        console.print("[red]❌ Some fixes failed[/red]")
        raise typer.Exit(code=1)
    
    # Run validation if requested
    if validate:
        console.print()
        console.print("[cyan]🧪 Running validation tests...[/cyan]")
        console.print()
        
        validate_cmd = [sys.executable, str(script_path), "--validate"]
        if model:
            validate_cmd.extend(["--model", model])
        
        validate_result = subprocess.run(validate_cmd, capture_output=False)
        
        if validate_result.returncode != 0:
            console.print()
            console.print("[yellow]⚠ Validation found issues (model may still have problems)[/yellow]")
            raise typer.Exit(code=1)
    
    console.print()
    console.print("[green]✓ Template fix complete![/green]")
    
    logger.info(
        "Model templates fixed",
        metadata={"model": model or "all", "validated": validate}
    )


@app.command()
def validate(
    model: Optional[str] = typer.Argument(
        None,
        help="Specific model to validate (optional, validates all if not specified)"
    ),
):
    """
    Validate models by testing them with a prompt.
    
    Sends a test question to each model and checks if the response
    is coherent. This helps detect models with broken templates
    or other configuration issues.
    
    Exit codes:
    - 0: All models validated successfully
    - 1: Some models failed validation
    """
    import subprocess
    
    console.print()
    console.print("[cyan]🧪 Validating models...[/cyan]")
    console.print()
    
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "fix_ollama_templates.py"
    
    if not script_path.exists():
        console.print(f"[red]ERROR: Script not found: {script_path}[/red]")
        raise typer.Exit(code=1)
    
    cmd = [sys.executable, str(script_path), "--validate"]
    if model:
        cmd.extend(["--model", model])
    
    result = subprocess.run(cmd, capture_output=False)
    
    raise typer.Exit(code=result.returncode)


if __name__ == "__main__":
    app()

