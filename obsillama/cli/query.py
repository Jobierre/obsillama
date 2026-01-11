"""
ObsIllama - Commande query

Cette commande permet d'effectuer des recherches sémantiques dans le vault
en utilisant les embeddings vectoriels stockés dans LanceDB.
"""

import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.table import Table
from rich.panel import Panel

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.storage.embedding_store import EmbeddingStore
from obsillama.llm.ollama_client import OllamaClient
from obsillama.utils.progress import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_panel,
    console,
)


@click.command()
@click.argument("query", type=str)
@click.option(
    "--category",
    type=str,
    default=None,
    help="Filtrer par catégorie (ex: 'Modélisation_3D_et_traitement')",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Nombre maximum de résultats à afficher (défaut: 10)",
)
@click.option(
    "--threshold",
    type=float,
    default=None,
    help="Seuil de similarité minimum (0.0-1.0, ex: 0.7)",
)
@click.option(
    "--folder",
    type=str,
    default=None,
    help="Filtrer par dossier (ex: 'Projects')",
)
@click.option(
    "--min-words",
    type=int,
    default=None,
    help="Nombre minimum de mots dans les notes",
)
@click.option(
    "--show-content",
    is_flag=True,
    help="Afficher un extrait du contenu de chaque note",
)
@pass_context
def query(
    ctx: ObsillamaContext,
    query: str,
    category: Optional[str],
    limit: int,
    threshold: Optional[float],
    folder: Optional[str],
    min_words: Optional[int],
    show_content: bool,
):
    """
    Recherche sémantique dans le vault.

    Cette commande utilise les embeddings vectoriels pour trouver les notes
    les plus pertinentes par rapport à votre requête.

    Exemples:
        obsillama query "self-hosting docker"
        obsillama query "machine learning" --limit 5 --threshold 0.75
        obsillama query "python" --category "Technology" --min-words 100
        obsillama query "projets 3D" --show-content
    """
    # En-tête
    print_header(f"🔍 Recherche Sémantique")
    print_info(f"Requête : [cyan]'{query}'[/cyan]")

    # Afficher les filtres actifs
    filters_active = []
    if category:
        filters_active.append(f"Catégorie: {category}")
    if folder:
        filters_active.append(f"Dossier: {folder}")
    if threshold:
        filters_active.append(f"Similarité minimum: {threshold}")
    if min_words:
        filters_active.append(f"Mots minimum: {min_words}")

    if filters_active:
        print_info(f"Filtres : {', '.join(filters_active)}")

    console.print()

    config = ctx.config
    start_time = time.time()

    try:
        # Initialiser les composants
        print_info("Initialisation de la recherche sémantique...")

        ollama_client = OllamaClient()
        lancedb_manager = LanceDBManager()
        embedding_store = EmbeddingStore(lancedb_manager)
        embedding_manager = EmbeddingManager(
            ollama_client=ollama_client,
            cache_path=Path("data/cache/embeddings.json"),
            model_name=config.ollama.models.embedding,
        )

        # Vérifier que la table notes existe
        if not lancedb_manager.table_exists("notes"):
            print_error(
                "La table 'notes' n'existe pas dans LanceDB.\n"
                "Exécutez d'abord 'obsillama embed' pour générer les embeddings."
            )
            sys.exit(1)

        # Compter le nombre total de notes
        total_notes = lancedb_manager.count_records("notes")
        print_info(f"Base de données : {total_notes} notes indexées")
        console.print()

        # Effectuer la recherche
        print_info("Génération de l'embedding de la requête...")

        results = embedding_store.search_by_text(
            query_text=query,
            embedding_generator=embedding_manager.generate_embedding,
            top_k=limit,
            similarity_threshold=threshold,
            category_filter=category,
            folder_filter=folder,
            min_word_count=min_words,
        )

        elapsed_time = time.time() - start_time

        # Afficher les résultats
        console.print()

        if not results:
            print_warning(
                "Aucun résultat trouvé pour votre requête.\n"
                "Essayez d'ajuster les filtres ou de reformuler votre requête."
            )
            sys.exit(0)

        # Créer un tableau des résultats
        table = Table(
            title=f"📊 Résultats de recherche ({len(results)} trouvés)",
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
        )

        table.add_column("Rang", style="dim", width=5, justify="center")
        table.add_column("Titre", style="cyan", min_width=30)
        table.add_column("Score", justify="right", style="green", width=8)
        table.add_column("Dossier", style="yellow", width=20)
        table.add_column("Mots", justify="right", style="magenta", width=8)

        for idx, result in enumerate(results, start=1):
            title = result.get("title", "Sans titre")
            similarity = result.get("_similarity", 0)
            folder_name = result.get("folder", "")
            word_count = result.get("word_count", 0)

            # Tronquer le titre si trop long
            if len(title) > 40:
                title = title[:37] + "..."

            # Tronquer le dossier si trop long
            if len(folder_name) > 18:
                folder_name = "..." + folder_name[-15:]

            # Code couleur pour le score
            if similarity >= 0.8:
                score_style = "bold green"
            elif similarity >= 0.6:
                score_style = "yellow"
            else:
                score_style = "dim"

            table.add_row(
                f"#{idx}",
                title,
                f"[{score_style}]{similarity:.3f}[/{score_style}]",
                folder_name or "-",
                f"{word_count:,}",
            )

        console.print(table)
        console.print()

        # Afficher le contenu si demandé
        if show_content:
            console.print()
            print_panel(
                "📄 Extraits de contenu",
                title="Aperçu des résultats",
                border_style="cyan",
            )

            for idx, result in enumerate(results[:5], start=1):  # Limiter à 5 pour ne pas surcharger
                title = result.get("title", "Sans titre")
                content = result.get("content", "")
                file_path = result.get("file_path", "")
                similarity = result.get("_similarity", 0)

                # Extraire les 200 premiers caractères
                content_preview = content[:200].replace("\n", " ")
                if len(content) > 200:
                    content_preview += "..."

                note_panel = Panel(
                    f"[bold cyan]Score:[/bold cyan] {similarity:.3f}\n"
                    f"[bold cyan]Fichier:[/bold cyan] [dim]{file_path}[/dim]\n\n"
                    f"[white]{content_preview}[/white]",
                    title=f"#{idx} - {title}",
                    border_style="blue",
                )
                console.print(note_panel)
                console.print()

        # Statistiques finales
        print_panel(
            f"✅ Recherche terminée en [bold cyan]{elapsed_time:.2f}s[/bold cyan]\n"
            f"📊 [bold]{len(results)}[/bold] résultats sur [dim]{total_notes}[/dim] notes indexées\n"
            f"🎯 Meilleur score : [bold green]{results[0].get('_similarity', 0):.3f}[/bold green]"
            + (f"\n🏆 Meilleur résultat : [cyan]{results[0].get('title', 'Sans titre')}[/cyan]" if results else ""),
            title="📈 Résumé",
            border_style="green",
        )

        # Conseils pour affiner la recherche
        if len(results) > 20 or (results and results[-1].get("_similarity", 0) < 0.5):
            console.print()
            print_info(
                "💡 [bold]Conseil[/bold] : Pour affiner votre recherche :\n"
                "   • Utilisez --threshold 0.7 pour filtrer les résultats peu pertinents\n"
                "   • Utilisez --category pour filtrer par catégorie\n"
                "   • Utilisez --limit 5 pour voir moins de résultats\n"
                "   • Soyez plus spécifique dans votre requête"
            )

    except Exception as e:
        print_error(f"Erreur lors de la recherche : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    query()
