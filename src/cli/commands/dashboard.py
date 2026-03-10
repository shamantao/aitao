"""
Dashboard command - AItao system overview at a glance.

Displays a rich, color-coded snapshot of:
- Services status (AiTao API, Meilisearch, Ollama, OpenWebUI, OnlyOffice)
- AI models currently loaded in Ollama memory
- Configured sources (include_paths) and their configured model
- Index statistics (Meilisearch docs vs LanceDB vectors)
- Worker / scan status and queue breakdown
- Recent errors (format errors vs content errors)
"""

import sys
import socket
import datetime
from pathlib import Path
from typing import Optional

# Ensure src path is available
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from cli.utils import get_config_path

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_get(url: str, timeout: float = 3.0):
    """Minimal HTTP GET — returns (status_code, json_body) or raises."""
    import requests
    resp = requests.get(url, timeout=timeout)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {}


def _fmt_count(n: int | None, singular: str = "doc", plural: str | None = None) -> str:
    """Format a count with its unit, e.g. '1 482 docs'."""
    if n is None:
        return "[dim]–[/dim]"
    unit = (plural or (singular + "s")) if n != 1 else singular
    return f"[bold]{n:,}[/bold] {unit}"


def _service_row(name: str, url: str, alive: bool, extra: str = "") -> Text:
    """Build a single colored service line."""
    icon = "[bold green]✓[/bold green]" if alive else "[bold red]✗[/bold red]"
    color = "green" if alive else "red"
    line = Text.assemble(
        Text.from_markup(icon + " "),
        Text(f"{name:<14}", style="bold"),
        Text(f"{url:<32}", style=color),
    )
    if extra:
        line.append(f"  {extra}", style="dim")
    return line


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _section_services(config) -> Panel:
    """Section: Services status (5 services)."""
    api_port   = int(config.get("api.port", 8200))
    ms_url     = config.get("meilisearch.url", "http://localhost:7700")
    ollama_url = config.get("llm.ollama_url", "http://localhost:11434")
    ms_port    = int(ms_url.split(":")[-1]) if ":" in ms_url else 7700
    ol_port    = int(ollama_url.split(":")[-1]) if ":" in ollama_url else 11434

    services = [
        ("AiTao API",   f"http://localhost:{api_port}", _port_open("localhost", api_port)),
        ("Meilisearch", ms_url,                          _port_open("localhost", ms_port)),
        ("Ollama",      ollama_url,                      _port_open("localhost", ol_port)),
        ("OpenWebUI",   "http://localhost:3000",          _port_open("localhost", 3000)),
        ("OnlyOffice",  "http://localhost:8080",          _port_open("localhost", 8080)),
    ]

    lines = [_service_row(name, url, alive) for name, url, alive in services]

    table = Table(box=None, show_header=False, padding=(0, 0))
    for line in lines:
        table.add_row(line)

    return Panel(table, title="[bold cyan]■ Services[/bold cyan]", border_style="cyan", expand=True)


def _section_models(ollama_url: str) -> Panel:
    """Section: AI models currently loaded in Ollama memory (GET /api/ps)."""
    rows = []
    try:
        status, data = _http_get(f"{ollama_url}/api/ps", timeout=2.0)
        models = data.get("models", []) if status == 200 else []
        if models:
            for m in models:
                name     = m.get("name", "?")
                size_mb  = round(m.get("size", 0) / 1024 / 1024)
                # expires_at is ISO 8601 optional
                expires  = ""
                if "expires_at" in m:
                    try:
                        exp = datetime.datetime.fromisoformat(m["expires_at"].replace("Z", "+00:00"))
                        delta = exp - datetime.datetime.now(datetime.timezone.utc)
                        mins  = max(0, int(delta.total_seconds() // 60))
                        expires = f"(expire dans {mins} min)" if mins > 0 else "(expire bientôt)"
                    except Exception:
                        pass
                rows.append(
                    Text.assemble(
                        Text("  [bold green]✓[/bold green] ", markup=True),
                        Text(f"{name:<30}", style="green bold"),
                        Text(f"{size_mb:>6} MB  ", style="dim"),
                        Text(expires, style="dim yellow"),
                    )
                )
        else:
            rows.append(Text("  Aucun modèle en mémoire (Ollama inactif ou idle)", style="dim"))
    except Exception:
        rows.append(Text("  Ollama non accessible", style="red dim"))

    table = Table(box=None, show_header=False, padding=(0, 0))
    for r in rows:
        table.add_row(r)

    return Panel(table, title="[bold cyan]■ Modèles Ollama en mémoire[/bold cyan]", border_style="cyan", expand=True)


def _section_index(config, ms_url: str) -> Panel:
    """Section: Index statistics (Meilisearch + LanceDB) and configured sources."""
    ms_docs    = None
    ms_version = "?"
    ldb_docs   = None

    # --- Meilisearch stats ---
    try:
        from search.meilisearch_client import MeilisearchClient
        from core.registry import StatsKeys
        client = MeilisearchClient()
        if client.is_healthy():
            ms_version = client.get_version()
            stats      = client.get_stats()
            ms_docs    = stats.get(StatsKeys.TOTAL_DOCUMENTS, 0)
    except Exception:
        pass

    # --- LanceDB stats ---
    try:
        from search.lancedb_client import LanceDBClient
        from core.registry import StatsKeys
        ldb  = LanceDBClient(load_model=False, ensure_table=False)
        stat = ldb.get_stats()
        ldb_docs = stat.get(StatsKeys.TOTAL_DOCUMENTS, 0)
    except Exception:
        pass

    # Diff indicator
    diff = ""
    if ms_docs is not None and ldb_docs is not None:
        d = ms_docs - ldb_docs
        if d == 0:
            diff = "[green]✓ Synchronisé[/green]"
        elif d > 0:
            diff = f"[yellow]⚠ {d:,} docs sans vecteur (indexation en cours?)[/yellow]"
        else:
            diff = f"[red]⚠ LanceDB a {abs(d):,} vecteurs orphelins[/red]"

    # --- include_paths ---
    paths = config.get("indexing.include_paths", []) or []

    # Build panel content
    table = Table(box=None, show_header=False, padding=(0, 0))
    table.add_row(
        Text("Meilisearch", style="bold"),
        Text.from_markup(f"  {_fmt_count(ms_docs)}  [dim]({ms_version})[/dim]"),
        Text("  = texte brut indexé, recherche par mots-clés", style="dim"),
    )
    table.add_row(
        Text("LanceDB", style="bold"),
        Text.from_markup(f"  {_fmt_count(ldb_docs, 'vecteur')}"),
        Text("  = représentation sémantique, comprend le sens", style="dim"),
    )
    if diff:
        table.add_row(Text(""), Text.from_markup(f"  {diff}"), Text(""))

    if paths:
        table.add_row(Text(""), Text(""), Text(""))
        table.add_row(
            Text("Sources", style="bold"),
            Text(f"  {len(paths)} dossier(s) configuré(s)", style="cyan"),
            Text(""),
        )
        for p in paths[:6]:
            table.add_row(Text(""), Text(f"  • {p}", style="dim"), Text(""))
        if len(paths) > 6:
            table.add_row(Text(""), Text(f"  … +{len(paths)-6} autres", style="dim italic"), Text(""))

    return Panel(table, title="[bold cyan]■ Index[/bold cyan]", border_style="cyan", expand=True)


def _section_worker(config) -> Panel:
    """Section: Worker status and queue breakdown."""
    try:
        from indexation.worker import BackgroundWorker
        worker      = BackgroundWorker(config_path=get_config_path())
        is_running  = worker.is_running()
        pid         = worker.get_pid()
        queue_stats = worker.queue.get_stats()

        pending    = queue_stats.get("pending", 0)
        processing = queue_stats.get("processing", 0)
        completed  = queue_stats.get("completed", 0)
        failed     = queue_stats.get("failed", 0)

        if is_running:
            w_text = Text.assemble(
                Text("● Worker ", style="bold"),
                Text("actif", style="bold green"),
                Text(f"  (PID {pid})", style="dim"),
            )
        else:
            w_text = Text.assemble(
                Text("● Worker ", style="bold"),
                Text("arrêté", style="bold red"),
            )

        table = Table(box=None, show_header=False, padding=(0, 0))
        table.add_row(w_text)
        table.add_row(Text(""))
        table.add_row(Text.from_markup(f"  En attente   [yellow]{pending:>6,}[/yellow]"))
        table.add_row(Text.from_markup(f"  En cours     [cyan]{processing:>6,}[/cyan]"))
        table.add_row(Text.from_markup(f"  Complétés    [green]{completed:>6,}[/green]"))
        table.add_row(Text.from_markup(f"  Échoués      [red]{failed:>6,}[/red]"))

    except Exception as e:
        table = Table(box=None, show_header=False, padding=(0, 0))
        table.add_row(Text(f"Erreur: {e}", style="red dim"))

    return Panel(table, title="[bold cyan]■ Worker / Scan[/bold cyan]", border_style="cyan", expand=True)


def _section_errors(config) -> Optional[Panel]:
    """Section: Recent failed tasks split by error type."""
    try:
        from indexation.worker import BackgroundWorker
        worker = BackgroundWorker(config_path=get_config_path())
        tasks  = worker.queue.list_tasks(status="failed", limit=100)

        if not tasks:
            return None

        # Classify: format error (unsupported extension) vs content error
        from collections import Counter
        format_counts: Counter = Counter()
        content_errors: list   = []

        format_keywords = [
            "unsupported", "not supported", "no extractor", "format",
            "UnsupportedFormat", "no handler", "handler returned false",
        ]

        for task in tasks:
            err = (task.error_message or "").lower()
            ext = Path(task.file_path).suffix.lower()
            if any(kw in err for kw in format_keywords) or ext in {".epub", ".mobi", ".azw", ".cbz", ".cbr"}:
                format_counts[ext or "(sans extension)"] += 1
            else:
                content_errors.append(task.file_path)

        table = Table(box=None, show_header=False, padding=(0, 0))

        if format_counts:
            total_fmt = sum(format_counts.values())
            table.add_row(Text.from_markup(
                f"[yellow]Format non supporté[/yellow] [dim](réessayable après mise à jour)[/dim]"
                f"  [bold]{total_fmt}[/bold] fichier(s)"
            ))
            for ext, cnt in format_counts.most_common(8):
                table.add_row(Text(f"    {ext}  ({cnt})", style="dim"))

        if content_errors:
            if format_counts:
                table.add_row(Text(""))
            table.add_row(Text.from_markup(
                f"[red]Erreur de contenu[/red] [dim](fichier corrompu / protégé)[/dim]"
                f"  [bold]{len(content_errors)}[/bold] fichier(s)"
            ))
            for fp in content_errors[:5]:
                p = Path(fp)
                # Truncate long paths
                display = str(p) if len(str(p)) < 60 else f"…/{p.parent.name}/{p.name}"
                table.add_row(Text(f"    {display}", style="dim"))
            if len(content_errors) > 5:
                table.add_row(Text(f"    … et {len(content_errors)-5} autres", style="dim italic"))

        return Panel(table, title="[bold red]■ Erreurs récentes[/bold red]", border_style="red", expand=True)

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def show_dashboard():
    """Render the full AiTao dashboard."""
    # Load config
    try:
        from core.config import ConfigManager
        config = ConfigManager(str(get_config_path()))
    except Exception as e:
        console.print(f"[red]Impossible de lire la config: {e}[/red]")
        return

    ollama_url = config.get("llm.ollama_url", "http://localhost:11434")
    ms_url     = config.get("meilisearch.url", "http://localhost:7700")

    # Header
    from core.version import get_version
    now = datetime.datetime.now().strftime("%d %b %Y  %H:%M")
    console.print()
    console.print(Panel(
        f"[bold white]AiTao Dashboard[/bold white]  [dim]—[/dim]  "
        f"[cyan]v{get_version()}[/cyan]  [dim]—[/dim]  [dim]{now}[/dim]",
        border_style="bright_cyan",
        expand=False,
    ))
    console.print()

    # Services + Models side-by-side
    services_panel = _section_services(config)
    models_panel   = _section_models(ollama_url)
    console.print(Columns([services_panel, models_panel], equal=True, expand=True))
    console.print()

    # Index + Worker side-by-side
    index_panel  = _section_index(config, ms_url)
    worker_panel = _section_worker(config)
    console.print(Columns([index_panel, worker_panel], equal=False, expand=True))
    console.print()

    # Errors (only if there are any)
    errors_panel = _section_errors(config)
    if errors_panel:
        console.print(errors_panel)
        console.print()

    console.print("[dim]Appuie sur Ctrl+C pour quitter.[/dim]")
    console.print()
