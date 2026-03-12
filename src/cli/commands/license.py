"""
AiTao — src/cli/commands/license.py

CLI commands for AiTao license management (end-user side).

Commands:
    ./aitao.sh license activate <KEY|FILE>  Install a license key or file
    ./aitao.sh license status               Show current license info
    ./aitao.sh license deactivate           Remove the installed key
"""

import typer
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich import box

from cli.utils import console

app = typer.Typer(
    name="license",
    help="Gérer la licence AiTao Premium.",
    no_args_is_help=True,
)


@app.command()
def activate(
    key_or_file: str = typer.Argument(..., help="Clé de licence (AITAO-xxx.yyy) ou chemin vers un fichier .key"),
):
    """Activer une licence Premium.

    Exemples:
        ./aitao.sh license activate AITAO-eyJ...xxx.sig
        ./aitao.sh license activate ~/Downloads/aitao-monnom.key
    """
    from core.license import LicenseManager

    # If it looks like a file path, read the key from it
    candidate = Path(key_or_file).expanduser()
    if candidate.exists() and candidate.is_file():
        key = candidate.read_text().strip()
        if not key:
            console.print("[red]✗ Le fichier est vide.[/red]")
            raise typer.Exit(1)
    else:
        key = key_or_file

    lm = LicenseManager()
    if not key.startswith("AITAO-"):
        console.print("[red]✗ Format invalide.[/red] La clé doit commencer par [bold]AITAO-[/bold]")
        raise typer.Exit(1)

    ok = lm.activate(key)
    if ok:
        info = lm.get_info()
        console.print(Panel(
            f"[bold green]✓ Licence Premium activée[/bold green]\n\n"
            f"  Tier   : [cyan]{info.get('tier', '?')}[/cyan]\n"
            f"  Valide jusqu'au : [cyan]{info.get('exp', '?')}[/cyan]\n"
            f"  Label  : {info.get('label', '?')}",
            title="AiTao Premium",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "[bold red]✗ Clé invalide ou expirée.[/bold red]\n\n"
            "Vérifiez que la clé est complète et non expirée.\n"
            "Contactez [cyan]support@auricacircular.com[/cyan] pour obtenir une nouvelle clé.",
            title="Erreur d'activation",
            border_style="red",
        ))
        raise typer.Exit(1)


@app.command()
def status():
    """Afficher le statut de la licence installée."""
    from core.license import LicenseManager

    lm = LicenseManager()
    edition = lm.edition()
    info = lm.get_info()

    if lm._beta_mode:
        console.print(Panel(
            "[bold cyan]Mode bêta actif[/bold cyan]\n\n"
            "Toutes les fonctionnalités Premium sont accessibles sans clé.\n"
            "Ce mode sera désactivé lors du lancement commercial.",
            title="AiTao — Licence",
            border_style="cyan",
        ))
        return

    if info:
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Champ", style="bold")
        table.add_column("Valeur")
        table.add_row("Édition", f"[green]{edition}[/green]")
        table.add_row("Tier", info.get("tier", "?"))
        table.add_row("Valide jusqu'au", info.get("exp", "?"))
        table.add_row("Label", info.get("label", "?"))
        console.print(Panel(table, title="AiTao — Licence", border_style="green"))
    else:
        console.print(Panel(
            "[yellow]Aucune licence installée.[/yellow]\n\n"
            "Édition : [bold]Core[/bold] (fonctionnalités de base uniquement)\n\n"
            "Pour activer Premium :\n"
            "  [green]./aitao.sh license activate AITAO-xxx.yyy[/green]",
            title="AiTao — Licence",
            border_style="yellow",
        ))


@app.command()
def deactivate():
    """Supprimer la licence installée (retour en mode Core)."""
    from core.license import LicenseManager

    lm = LicenseManager()
    if not lm.get_info():
        console.print("[yellow]Aucune licence active à désactiver.[/yellow]")
        return

    confirm = typer.confirm("Supprimer la licence Premium ? (retour en mode Core)")
    if confirm:
        lm.deactivate()
        console.print("[green]✓ Licence supprimée.[/green] Mode Core actif.")
    else:
        console.print("Annulé.")
