"""
ObsIllama - Commande stats

Cette commande affiche des statistiques détaillées sur le vault,
les catégories, les embeddings et le graphe GraphRAG.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

import click
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import BarColumn
from rich import box

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.note_scanner import NoteScanner
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.storage.embedding_store import EmbeddingStore
from obsillama.storage.category_store import CategoryStore
from obsillama.storage.graph_store import GraphStore
from obsillama.utils.progress import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_panel,
    console,
)


def create_ascii_bar(value: int, max_value: int, width: int = 20) -> str:
    """
    Crée une barre ASCII pour visualiser une valeur.

    Args:
        value: Valeur à afficher
        max_value: Valeur maximum pour le calcul du pourcentage
        width: Largeur de la barre en caractères

    Returns:
        str: Barre ASCII formatée
    """
    if max_value == 0:
        filled = 0
    else:
        filled = int((value / max_value) * width)

    bar = "█" * filled + "░" * (width - filled)
    percentage = (value / max_value * 100) if max_value > 0 else 0

    return f"[cyan]{bar}[/cyan] [dim]{percentage:.0f}%[/dim]"


def format_number(num: int) -> str:
    """Formate un nombre avec des séparateurs de milliers."""
    return f"{num:,}".replace(",", " ")


@click.command()
@click.option(
    "--vault",
    is_flag=True,
    help="Afficher les statistiques du vault (notes, mots, dossiers)",
)
@click.option(
    "--categories",
    is_flag=True,
    help="Afficher les statistiques des catégories",
)
@click.option(
    "--embeddings",
    is_flag=True,
    help="Afficher les statistiques des embeddings",
)
@click.option(
    "--graphrag",
    is_flag=True,
    help="Afficher les statistiques GraphRAG (entités, relations)",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Afficher toutes les statistiques (défaut si aucune option)",
)
@pass_context
def stats(
    ctx: ObsillamaContext,
    vault: bool,
    categories: bool,
    embeddings: bool,
    graphrag: bool,
    show_all: bool,
):
    """
    Affiche des statistiques détaillées sur le projet ObsIllama.

    Cette commande analyse les données du projet et affiche:
    - Statistiques du vault (notes, taille, dossiers)
    - Statistiques des catégories (distribution, couverture)
    - Statistiques des embeddings (index, dimension)
    - Statistiques GraphRAG (entités, relations, communautés)

    Exemples:
        obsillama stats
        obsillama stats --vault
        obsillama stats --categories --embeddings
        obsillama stats --all
    """
    # En-tête
    print_header("📊 Statistiques ObsIllama")
    console.print()

    config = ctx.config

    # Si aucune option n'est spécifiée, afficher tout
    if not any([vault, categories, embeddings, graphrag]):
        show_all = True

    if show_all:
        vault = categories = embeddings = graphrag = True

    try:
        # ====================================================================
        # Statistiques du Vault
        # ====================================================================
        if vault:
            print_info("📁 Chargement des statistiques du vault...")

            vault_path = Path(config.vault.path)
            cache_dir = Path("data/cache")
            cache_file = cache_dir / "scanned_notes.json"

            # Charger les notes scannées si disponibles
            notes = []
            if cache_file.exists():
                scanner = NoteScanner(
                    vault_path=vault_path,
                    exclude_folders=config.vault.exclude_folders,
                    cache_path=cache_file,
                )
                try:
                    notes = scanner.load_cache()
                    print_success(f"{len(notes)} notes chargées depuis le cache")
                except Exception:
                    print_warning("Cache non disponible - exécutez 'obsillama scan'")
            else:
                print_warning("Cache non disponible - exécutez 'obsillama scan'")

            if notes:
                # Calculer les statistiques
                total_notes = len(notes)
                total_words = sum(note.word_count for note in notes)
                avg_words = total_words // total_notes if total_notes > 0 else 0

                # Compter les dossiers
                folders = Counter(note.folder for note in notes if note.folder)
                top_folders = folders.most_common(10)

                # Compter les tags
                all_tags = []
                for note in notes:
                    all_tags.extend(note.tags)
                tags_counter = Counter(all_tags)
                top_tags = tags_counter.most_common(10)

                # Afficher un panel récapitulatif
                vault_panel = Panel(
                    f"[cyan]Notes totales :[/cyan] [bold]{format_number(total_notes)}[/bold]\n"
                    f"[cyan]Mots totaux :[/cyan] [bold]{format_number(total_words)}[/bold]\n"
                    f"[cyan]Mots par note (moy.) :[/cyan] [bold]{format_number(avg_words)}[/bold]\n"
                    f"[cyan]Dossiers :[/cyan] [bold]{len(folders)}[/bold]\n"
                    f"[cyan]Tags uniques :[/cyan] [bold]{len(tags_counter)}[/bold]",
                    title="📁 Statistiques du Vault",
                    border_style="blue",
                    box=box.ROUNDED,
                )
                console.print(vault_panel)
                console.print()

                # Top 10 dossiers
                if top_folders:
                    table = Table(
                        title="📂 Top 10 Dossiers",
                        box=box.SIMPLE,
                        show_header=True,
                        header_style="bold cyan",
                    )
                    table.add_column("Rang", justify="center", style="dim", width=6)
                    table.add_column("Dossier", style="cyan", min_width=30)
                    table.add_column("Notes", justify="right", style="green", width=10)
                    table.add_column("Distribution", width=25)

                    max_count = top_folders[0][1]
                    for idx, (folder, count) in enumerate(top_folders, start=1):
                        folder_display = folder if folder else "[dim](racine)[/dim]"
                        bar = create_ascii_bar(count, max_count, width=15)
                        table.add_row(f"#{idx}", folder_display, str(count), bar)

                    console.print(table)
                    console.print()

                # Top 10 tags
                if top_tags:
                    table = Table(
                        title="🏷️  Top 10 Tags",
                        box=box.SIMPLE,
                        show_header=True,
                        header_style="bold cyan",
                    )
                    table.add_column("Rang", justify="center", style="dim", width=6)
                    table.add_column("Tag", style="yellow", min_width=30)
                    table.add_column("Occurrences", justify="right", style="green", width=12)
                    table.add_column("Distribution", width=25)

                    max_count = top_tags[0][1]
                    for idx, (tag, count) in enumerate(top_tags, start=1):
                        bar = create_ascii_bar(count, max_count, width=15)
                        table.add_row(f"#{idx}", tag, str(count), bar)

                    console.print(table)
                    console.print()

        # ====================================================================
        # Statistiques des Catégories
        # ====================================================================
        if categories:
            print_info("🗂️  Chargement des statistiques des catégories...")

            category_store = CategoryStore()
            taxonomy_file = Path("data/categories/taxonomy.json")
            assignments_file = Path("data/categories/assignments.json")

            if taxonomy_file.exists():
                cats = category_store.load_taxonomy()
                print_success(f"{len(cats)} catégories chargées")

                if cats:
                    # Statistiques générales
                    approved = sum(1 for c in cats if c.review_status == "approved")
                    pending = sum(1 for c in cats if c.review_status == "pending")
                    rejected = sum(1 for c in cats if c.review_status == "rejected")

                    total_assigned = sum(c.note_count for c in cats)
                    avg_confidence = (
                        sum(c.avg_confidence for c in cats) / len(cats) if cats else 0
                    )

                    # Panel récapitulatif
                    cat_panel = Panel(
                        f"[cyan]Total catégories :[/cyan] [bold]{len(cats)}[/bold]\n"
                        f"[green]Approuvées :[/green] [bold]{approved}[/bold]\n"
                        f"[yellow]En attente :[/yellow] [bold]{pending}[/bold]\n"
                        f"[red]Rejetées :[/red] [bold]{rejected}[/bold]\n"
                        f"[cyan]Notes assignées :[/cyan] [bold]{total_assigned}[/bold]\n"
                        f"[cyan]Confiance moyenne :[/cyan] [bold]{avg_confidence:.1%}[/bold]",
                        title="🗂️  Statistiques des Catégories",
                        border_style="green",
                        box=box.ROUNDED,
                    )
                    console.print(cat_panel)
                    console.print()

                    # Top catégories par nombre de notes
                    sorted_cats = sorted(cats, key=lambda c: c.note_count, reverse=True)[:10]

                    if sorted_cats:
                        table = Table(
                            title="📊 Top 10 Catégories (par notes assignées)",
                            box=box.SIMPLE,
                            show_header=True,
                            header_style="bold cyan",
                        )
                        table.add_column("Rang", justify="center", style="dim", width=6)
                        table.add_column("Nom", style="cyan", min_width=30)
                        table.add_column("Notes", justify="right", style="green", width=8)
                        table.add_column("Conf.", justify="right", style="yellow", width=8)
                        table.add_column("Statut", justify="center", width=12)

                        for idx, cat in enumerate(sorted_cats, start=1):
                            # Code couleur pour le statut
                            if cat.review_status == "approved":
                                status = "[green]✓ Approuvé[/green]"
                            elif cat.review_status == "rejected":
                                status = "[red]✗ Rejeté[/red]"
                            else:
                                status = "[yellow]⏳ Pending[/yellow]"

                            table.add_row(
                                f"#{idx}",
                                cat.name[:35] + "..." if len(cat.name) > 35 else cat.name,
                                str(cat.note_count),
                                f"{cat.avg_confidence:.1%}",
                                status,
                            )

                        console.print(table)
                        console.print()

            else:
                print_warning(
                    "Aucune taxonomie trouvée - exécutez 'obsillama analyze' d'abord"
                )
                console.print()

        # ====================================================================
        # Statistiques des Embeddings
        # ====================================================================
        if embeddings:
            print_info("🧠 Chargement des statistiques des embeddings...")

            lancedb_manager = LanceDBManager()
            embedding_store = EmbeddingStore(lancedb_manager)

            stats_emb = embedding_store.get_embedding_stats()
            print_success("Statistiques des embeddings chargées")

            # Panel récapitulatif
            emb_panel = Panel(
                f"[cyan]Notes avec embeddings :[/cyan] [bold]{format_number(stats_emb['notes_with_embeddings'])}[/bold]\n"
                f"[cyan]Total catégories :[/cyan] [bold]{stats_emb['total_categories']}[/bold]\n"
                f"[cyan]Tables LanceDB :[/cyan] [bold]{len(stats_emb['tables'])}[/bold]\n"
                f"[dim]Tables : {', '.join(stats_emb['tables'])}[/dim]",
                title="🧠 Statistiques des Embeddings",
                border_style="magenta",
                box=box.ROUNDED,
            )
            console.print(emb_panel)
            console.print()

        # ====================================================================
        # Statistiques GraphRAG
        # ====================================================================
        if graphrag:
            print_info("🕸️  Chargement des statistiques GraphRAG...")

            graph_file = Path("data/categories/graph_relationships.json")

            if graph_file.exists():
                try:
                    with open(graph_file, "r", encoding="utf-8") as f:
                        graph_data = json.load(f)

                    entities = graph_data.get("entities", [])
                    relationships = graph_data.get("relationships", [])
                    communities = graph_data.get("communities", [])

                    print_success(
                        f"{len(entities)} entités, {len(relationships)} relations, "
                        f"{len(communities)} communautés"
                    )

                    # Compter les types d'entités
                    entity_types = Counter(e.get("type", "unknown") for e in entities)

                    # Panel récapitulatif
                    graph_panel = Panel(
                        f"[cyan]Entités extraites :[/cyan] [bold]{format_number(len(entities))}[/bold]\n"
                        f"[cyan]Relations :[/cyan] [bold]{format_number(len(relationships))}[/bold]\n"
                        f"[cyan]Communautés :[/cyan] [bold]{len(communities)}[/bold]\n"
                        f"[cyan]Types d'entités :[/cyan] [bold]{len(entity_types)}[/bold]",
                        title="🕸️  Statistiques GraphRAG",
                        border_style="yellow",
                        box=box.ROUNDED,
                    )
                    console.print(graph_panel)
                    console.print()

                    # Distribution des types d'entités
                    if entity_types:
                        table = Table(
                            title="📈 Distribution des Types d'Entités",
                            box=box.SIMPLE,
                            show_header=True,
                            header_style="bold cyan",
                        )
                        table.add_column("Type", style="cyan", min_width=20)
                        table.add_column("Nombre", justify="right", style="green", width=10)
                        table.add_column("Distribution", width=30)

                        max_count = entity_types.most_common(1)[0][1]
                        for entity_type, count in entity_types.most_common():
                            bar = create_ascii_bar(count, max_count, width=20)
                            table.add_row(entity_type.capitalize(), str(count), bar)

                        console.print(table)
                        console.print()

                except Exception as e:
                    print_error(f"Erreur lors de la lecture du graphe : {e}")
                    console.print()
            else:
                print_warning(
                    "Aucun graphe GraphRAG trouvé - exécutez 'obsillama analyze' d'abord"
                )
                console.print()

        # Résumé final
        print_panel(
            "✅ Statistiques générées avec succès\n\n"
            "💡 [bold]Astuce[/bold] : Utilisez les options pour filtrer l'affichage :\n"
            "   • --vault        : Statistiques du vault uniquement\n"
            "   • --categories   : Statistiques des catégories uniquement\n"
            "   • --embeddings   : Statistiques des embeddings uniquement\n"
            "   • --graphrag     : Statistiques GraphRAG uniquement",
            title="📊 Terminé",
            border_style="green",
        )

    except Exception as e:
        print_error(f"Erreur lors de la génération des statistiques : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    stats()
