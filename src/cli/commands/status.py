"""
Status command - Show AItao system status.

Displays the health of all components:
- Configuration
- Meilisearch server
- LanceDB database
- Python environment
- API server
"""

import sys
import socket
from pathlib import Path

from rich.table import Table

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils import (
    console, print_header, success, error, warning, info,
    status_line, create_table, get_config_path, spinner
)
from core.registry import StatsKeys


def show_status():
    """Display comprehensive system status."""
    print_header("AItao Status", "System health check")
    console.print()
    
    # Version info
    _show_version_info()
    console.print()
    
    # Configuration status
    _show_config_status()
    console.print()

    # API status
    _show_api_status()
    console.print()
    
    # Meilisearch status
    _show_meilisearch_status()
    console.print()
    
    # LanceDB status  
    _show_lancedb_status()
    console.print()
    
    # Python environment
    _show_python_info()


def _show_version_info():
    """Show version information."""
    console.print("[bold]Version[/bold]")
    try:
        from core.version import get_version, get_version_info
        ver = get_version()
        info_dict = get_version_info()
        status_line("Version", ver)
        status_line("Python", info_dict.get("python_version", "unknown"))
    except Exception as e:
        status_line("Version", f"Error: {e}", ok=False)


def _show_config_status():
    """Show configuration status."""
    console.print("[bold]Configuration[/bold]")
    try:
        from core.config import ConfigManager
        config_path = get_config_path()
        config = ConfigManager(str(config_path))
        status_line("Config file", str(config_path.relative_to(config_path.parent.parent)))
        
        storage_root = config.get("paths.storage_root", "Not set")
        status_line("Storage root", storage_root)
        
        # Quick check if storage exists
        from pathlib import Path
        storage_path = Path(storage_root).expanduser()
        if storage_path.exists():
            status_line("Storage exists", "Yes")
        else:
            status_line("Storage exists", "No (will be created)", ok=False)
            
    except FileNotFoundError:
        status_line("Config file", "Not found", ok=False)
    except Exception as e:
        status_line("Config", f"Error: {e}", ok=False)


def _show_meilisearch_status():
    """Show Meilisearch status."""
    console.print("[bold]Meilisearch[/bold]")
    try:
        from search.meilisearch_client import MeilisearchClient
        
        # Try to connect
        with spinner("Connecting to Meilisearch..."):
            client = MeilisearchClient()
        
        if client.is_healthy():
            status_line("Server", "Running")
            status_line("Version", client.get_version())
            status_line("URL", client.host)
            
            # Get stats
            stats = client.get_stats()
            status_line("Index", client.index_name)
            status_line("Documents", str(stats.get(StatsKeys.TOTAL_DOCUMENTS, 0)))
        else:
            status_line("Server", "Not responding", ok=False)
            
    except Exception as e:
        status_line("Server", f"Not available: {e}", ok=False)
        info("  Start with: brew services start meilisearch")


def _show_api_status():
    """Show API status."""
    console.print("[bold]API Server[/bold]")
    try:
        import requests
        from core.config import get_config

        config = get_config()
        port = config.get("api.port", 8200)
        port = int(port) if isinstance(port, (int, str)) else 8200
        base_url = f"http://localhost:{port}"

        def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
            """Check if a local TCP port is open."""
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except OSError:
                return False

        if not _is_port_open("localhost", port):
            status_line("Status", "Not running", ok=False)
            status_line("URL", base_url, ok=False)
            info("  Start with: ./aitao.sh api start")
            return

        try:
            response = requests.get(f"{base_url}/api/health", timeout=(1, 5))
            if response.status_code == 200:
                status_line("Status", "Running")
                status_line("URL", base_url)
            else:
                status_line("Status", f"Unhealthy ({response.status_code})", ok=False)
                status_line("URL", base_url, ok=False)
        except requests.ReadTimeout:
            status_line("Status", "Running (slow health check)")
            status_line("URL", base_url)
        except requests.RequestException as e:
            status_line("Status", "Running (health check failed)", ok=False)
            status_line("URL", base_url, ok=False)
            info(f"  Health error: {e}")
    except Exception as e:
        status_line("Status", f"Error: {e}", ok=False)
        info("  Start with: ./aitao.sh api start")


def _show_lancedb_status():
    """Show LanceDB status."""
    console.print("[bold]LanceDB (Vector Search)[/bold]")
    try:
        from search.lancedb_client import LanceDBClient
        
        with spinner("Loading embedding model..."):
            client = LanceDBClient()
        stats = client.get_stats()
        
        status_line("Database", str(client.db_path))
        status_line("Table", client.table_name)
        status_line("Documents", str(stats.get(StatsKeys.TOTAL_DOCUMENTS, 0)))
        status_line("Embedding dim", str(stats.get(StatsKeys.EMBEDDING_DIMENSION, 0)))
        
    except Exception as e:
        status_line("Database", f"Error: {e}", ok=False)


def _show_python_info():
    """Show Python environment info."""
    console.print("[bold]Python Environment[/bold]")
    import sys
    status_line("Python", sys.version.split()[0])
    status_line("Executable", sys.executable)
    
    # Check key packages
    packages = ["typer", "meilisearch", "lancedb", "sentence_transformers"]
    for pkg in packages:
        try:
            module = __import__(pkg.replace("-", "_"))
            ver = getattr(module, "__version__", "installed")
            status_line(pkg, ver)
        except ImportError:
            status_line(pkg, "Not installed", ok=False)
