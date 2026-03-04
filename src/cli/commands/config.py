"""
Configuration management commands.

Commands:
- aitao config show     Show current configuration
- aitao config validate Validate configuration file
- aitao config edit     Open config in editor
"""

import sys
from pathlib import Path

import typer
from rich.syntax import Syntax

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils import console, success, error, warning, info, print_header

# Resolve project root from file location (CWD may be src/ when launched via aitao.sh)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"
_CONFIG_TEMPLATE = _PROJECT_ROOT / "config" / "config.yaml.template"


app = typer.Typer(help="Configuration management", no_args_is_help=True)


@app.command("show")
def show_config(
    section: str = typer.Argument(None, help="Config section to show (e.g., 'search')"),
):
    """Show current configuration."""
    try:
        from core.config import ConfigManager
        config = ConfigManager(str(_CONFIG_PATH))
        
        if section:
            data = config.get_section(section)
            if data:
                import yaml
                output = yaml.dump(data, default_flow_style=False, allow_unicode=True)
                syntax = Syntax(output, "yaml", theme="monokai")
                console.print(syntax)
            else:
                error(f"Section '{section}' not found")
        else:
            # Show full config
            if _CONFIG_PATH.exists():
                syntax = Syntax(_CONFIG_PATH.read_text(), "yaml", theme="monokai")
                console.print(syntax)
                
    except FileNotFoundError:
        error("Config file not found: config/config.yaml")
        info("Run: cp config/config.yaml.template config/config.yaml")
    except Exception as e:
        error(f"Error reading config: {e}")


@app.command("validate")
def validate_config():
    """Validate configuration file."""
    print_header("Configuration Validation")
    
    errors = []
    warnings = []
    
    try:
        from core.config import ConfigManager
        config = ConfigManager(str(_CONFIG_PATH))
        success("Config file parsed successfully")
        
        # Check required sections
        required_sections = ["paths", "search", "indexing"]
        for section in required_sections:
            if config.get_section(section):
                success(f"Section '{section}' present")
            else:
                errors.append(f"Missing required section: {section}")
        
        # Check paths
        storage_root = config.get("paths.storage_root")
        if storage_root:
            path = Path(storage_root).expanduser()
            if path.exists():
                success(f"Storage root exists: {storage_root}")
            else:
                warnings.append(f"Storage root does not exist: {storage_root}")
        else:
            errors.append("paths.storage_root not configured")
        
        # Check Meilisearch URL
        ms_url = config.get("search.meilisearch.url")
        if ms_url:
            success(f"Meilisearch URL: {ms_url}")
        else:
            warnings.append("search.meilisearch.url not configured")
        
        console.print()
        
        if errors:
            for err in errors:
                error(err)
        if warnings:
            for warn in warnings:
                warning(warn)
        
        if not errors:
            success("Configuration is valid!")
            raise typer.Exit(0)
        else:
            error(f"Found {len(errors)} error(s)")
            raise typer.Exit(1)
            
    except FileNotFoundError:
        error(f"Config file not found: {_CONFIG_PATH}")
        raise typer.Exit(1)


@app.command("edit")
def edit_config():
    """Open config file in default editor."""
    import subprocess
    import os
    
    if not _CONFIG_PATH.exists():
        error("Config file not found")
        if typer.confirm("Create from template?"):
            if _CONFIG_TEMPLATE.exists():
                import shutil
                shutil.copy(_CONFIG_TEMPLATE, _CONFIG_PATH)
                success(f"Created {_CONFIG_PATH} from template")
            else:
                error("Template not found")
                raise typer.Exit(1)
        else:
            raise typer.Exit(1)
    
    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(_CONFIG_PATH)])
