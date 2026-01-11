"""
ObsIllama - Progress & Display Utilities

Ce module fournit des fonctions helper pour créer des progress bars,
des tableaux, et des messages formatés avec Rich.
"""

from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import click


# Console Rich par défaut
console = Console()


# ============================================================================
# Progress bars
# ============================================================================


@contextmanager
def create_progress(description: str = "Processing..."):
    """
    Crée une progress bar Rich avec colonnes personnalisées.

    Args:
        description: Description de la tâche en cours

    Yields:
        Progress: Contexte de progress bar

    Example:
        with create_progress("Scanning notes") as progress:
            task = progress.add_task("Scan", total=100)
            for i in range(100):
                progress.update(task, advance=1)
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="bold green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        yield progress


def track_progress(sequence, description: str = "Processing..."):
    """
    Wrapper simple pour tracker une séquence avec une progress bar.

    Args:
        sequence: Séquence à itérer
        description: Description de la tâche

    Yields:
        Items de la séquence

    Example:
        for item in track_progress(items, "Processing items"):
            process(item)
    """
    from rich.progress import track

    return track(sequence, description=description, console=console)


# ============================================================================
# Tables
# ============================================================================


def create_table(
    title: str,
    columns: List[Dict[str, Any]],
    rows: List[List[str]],
    show_header: bool = True,
    show_footer: bool = False,
) -> Table:
    """
    Crée une table Rich formatée.

    Args:
        title: Titre de la table
        columns: Liste de specs de colonnes (name, style, justify, etc.)
        rows: Liste de lignes (chaque ligne = liste de strings)
        show_header: Afficher l'en-tête
        show_footer: Afficher le pied de page

    Returns:
        Table Rich configurée

    Example:
        table = create_table(
            "Notes Statistics",
            columns=[
                {"name": "Category", "style": "cyan"},
                {"name": "Count", "justify": "right", "style": "green"}
            ],
            rows=[
                ["Technology", "150"],
                ["Personal", "80"]
            ]
        )
        console.print(table)
    """
    table = Table(
        title=title,
        show_header=show_header,
        show_footer=show_footer,
        header_style="bold magenta",
        box=box.ROUNDED,
    )

    # Ajouter les colonnes
    for col in columns:
        name = col.pop("name")
        table.add_column(name, **col)

    # Ajouter les lignes
    for row in rows:
        table.add_row(*row)

    return table


def print_table(
    title: str,
    columns: List[Dict[str, Any]],
    rows: List[List[str]],
    **kwargs,
):
    """
    Crée et affiche une table directement.

    Args:
        title: Titre de la table
        columns: Liste de specs de colonnes
        rows: Liste de lignes
        **kwargs: Arguments supplémentaires pour create_table
    """
    table = create_table(title, columns, rows, **kwargs)
    console.print(table)


# ============================================================================
# Messages formatés
# ============================================================================


def print_success(message: str):
    """Affiche un message de succès."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Affiche un message d'erreur."""
    console.print(f"[red]✗[/red] {message}", style="bold red")


def print_warning(message: str):
    """Affiche un avertissement."""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


def print_info(message: str):
    """Affiche une information."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_step(step_num: int, total_steps: int, message: str):
    """Affiche une étape d'un processus."""
    console.print(f"[cyan][{step_num}/{total_steps}][/cyan] {message}")


# ============================================================================
# Panels et sections
# ============================================================================


def print_panel(
    content: str,
    title: Optional[str] = None,
    border_style: str = "blue",
    expand: bool = False,
):
    """
    Affiche un panel Rich.

    Args:
        content: Contenu du panel
        title: Titre optionnel
        border_style: Style de la bordure
        expand: Étendre sur toute la largeur
    """
    panel = Panel(
        content,
        title=title,
        border_style=border_style,
        expand=expand,
        box=box.ROUNDED,
    )
    console.print(panel)


def print_header(text: str):
    """Affiche un en-tête de section."""
    console.print()
    console.rule(f"[bold cyan]{text}[/bold cyan]", style="cyan")
    console.print()


# ============================================================================
# Statistiques et résumés
# ============================================================================


def print_stats(stats: Dict[str, Any], title: str = "Statistics"):
    """
    Affiche des statistiques sous forme de tableau.

    Args:
        stats: Dictionnaire clé -> valeur
        title: Titre du tableau

    Example:
        print_stats({
            "Total notes": 800,
            "Categories": 20,
            "Coverage": "95%"
        })
    """
    table = Table(title=title, box=box.SIMPLE, show_header=False)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green", justify="right")

    for key, value in stats.items():
        table.add_row(key, str(value))

    console.print(table)


def print_summary(
    title: str,
    items: List[str],
    border_style: str = "green",
):
    """
    Affiche un résumé avec liste à puces.

    Args:
        title: Titre du résumé
        items: Liste d'items à afficher
        border_style: Style de la bordure
    """
    content = "\n".join(f"• {item}" for item in items)
    print_panel(content, title=title, border_style=border_style)


# ============================================================================
# Interactions utilisateur
# ============================================================================


def confirm(
    message: str,
    default: bool = False,
    abort: bool = False,
) -> bool:
    """
    Demande confirmation à l'utilisateur.

    Args:
        message: Message à afficher
        default: Valeur par défaut
        abort: Si True, quitte le programme si l'utilisateur refuse

    Returns:
        True si l'utilisateur confirme, False sinon

    Example:
        if confirm("Voulez-vous continuer ?"):
            # Continuer
    """
    result = click.confirm(
        click.style(f"❓ {message}", fg="yellow"),
        default=default,
        abort=abort,
    )
    return result


def prompt(
    message: str,
    default: Optional[str] = None,
    type=str,
) -> Any:
    """
    Demande une valeur à l'utilisateur.

    Args:
        message: Message à afficher
        default: Valeur par défaut
        type: Type de la valeur attendue

    Returns:
        Valeur saisie par l'utilisateur

    Example:
        name = prompt("Nom de la catégorie", default="Technology")
    """
    return click.prompt(
        click.style(f"❓ {message}", fg="cyan"),
        default=default,
        type=type,
    )


# ============================================================================
# Formatage de données
# ============================================================================


def format_size(bytes: int) -> str:
    """
    Formate une taille en octets en format lisible.

    Args:
        bytes: Taille en octets

    Returns:
        Taille formatée (ex: "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """
    Formate une durée en secondes en format lisible.

    Args:
        seconds: Durée en secondes

    Returns:
        Durée formatée (ex: "1m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Formate un pourcentage.

    Args:
        value: Valeur entre 0 et 1
        decimals: Nombre de décimales

    Returns:
        Pourcentage formaté (ex: "95.5%")
    """
    return f"{value * 100:.{decimals}f}%"


# ============================================================================
# Export pour faciliter les imports
# ============================================================================

__all__ = [
    "console",
    "create_progress",
    "track_progress",
    "create_table",
    "print_table",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_step",
    "print_panel",
    "print_header",
    "print_stats",
    "print_summary",
    "confirm",
    "prompt",
    "format_size",
    "format_duration",
    "format_percentage",
]
