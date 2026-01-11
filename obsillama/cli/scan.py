"""
ObsIllama - Commande scan

Cette commande scanne le vault Obsidian et parse les notes.
"""

import sys
from pathlib import Path
from typing import Optional, Literal
from collections import Counter

import click

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.note_scanner import NoteScanner
from obsillama.utils.progress import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_step,
    print_stats,
    print_table,
    print_summary,
    print_panel,
    track_progress,
    console,
)


def compute_statistics(notes):
    """
    Calcule les statistiques sur les notes scannées.

    Args:
        notes: Liste des notes parsées

    Returns:
        Dict contenant les statistiques
    """
    if not notes:
        return {}

    # Statistiques de base
    total_notes = len(notes)
    total_words = sum(note.word_count for note in notes)
    avg_words = total_words / total_notes if total_notes > 0 else 0

    # Tags
    all_tags = []
    for note in notes:
        all_tags.extend(note.tags)
    unique_tags = len(set(all_tags))

    # Liens
    total_backlinks = sum(len(note.backlinks) for note in notes)
    avg_backlinks = total_backlinks / total_notes if total_notes > 0 else 0

    # Dossiers
    folders = [note.folder for note in notes if note.folder]
    unique_folders = len(set(folders))

    # Notes avec/sans tags
    notes_with_tags = sum(1 for note in notes if note.tags)
    notes_without_tags = total_notes - notes_with_tags

    return {
        "total_notes": total_notes,
        "total_words": total_words,
        "avg_words": int(avg_words),
        "unique_tags": unique_tags,
        "total_tags": len(all_tags),
        "total_backlinks": total_backlinks,
        "avg_backlinks": round(avg_backlinks, 1),
        "unique_folders": unique_folders,
        "notes_with_tags": notes_with_tags,
        "notes_without_tags": notes_without_tags,
    }


def display_top_items(notes, top_n: int = 10):
    """
    Affiche les top tags et dossiers.

    Args:
        notes: Liste des notes
        top_n: Nombre d'items à afficher
    """
    if not notes:
        return

    # Top tags
    all_tags = []
    for note in notes:
        all_tags.extend(note.tags)

    if all_tags:
        tag_counter = Counter(all_tags)
        top_tags = tag_counter.most_common(top_n)

        print_table(
            title=f"Top {min(top_n, len(top_tags))} Tags",
            columns=[
                {"name": "Tag", "style": "cyan"},
                {"name": "Count", "justify": "right", "style": "green"},
            ],
            rows=[[tag, str(count)] for tag, count in top_tags],
        )
        console.print()

    # Top dossiers
    folders = [note.folder for note in notes if note.folder]

    if folders:
        folder_counter = Counter(folders)
        top_folders = folder_counter.most_common(top_n)

        # Tronquer les noms de dossiers trop longs
        truncated_folders = []
        for folder, count in top_folders:
            if len(folder) > 40:
                folder = "..." + folder[-37:]
            truncated_folders.append([folder, str(count)])

        print_table(
            title=f"Top {min(top_n, len(top_folders))} Dossiers",
            columns=[
                {"name": "Folder", "style": "cyan"},
                {"name": "Notes", "justify": "right", "style": "green"},
            ],
            rows=truncated_folders,
        )
        console.print()


@click.command()
@click.option(
    "--all",
    "scan_all",
    is_flag=True,
    help="Scanner toutes les notes du vault",
)
@click.option(
    "--sample",
    type=int,
    help="Nombre de notes à échantillonner (échantillonnage aléatoire)",
)
@click.option(
    "--percent",
    type=click.IntRange(1, 100),
    help="Pourcentage de notes à échantillonner (échantillonnage stratifié)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Forcer le scan même si un cache existe",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Ne pas sauvegarder dans le cache",
)
@click.option(
    "--top",
    type=int,
    default=10,
    help="Nombre de top items à afficher (tags, dossiers)",
)
@pass_context
def scan(
    ctx: ObsillamaContext,
    scan_all: bool,
    sample: Optional[int],
    percent: Optional[int],
    force: bool,
    no_cache: bool,
    top: int,
):
    """
    Scanne le vault Obsidian et parse les notes.

    Cette commande analyse votre vault et crée un cache des notes
    pour accélérer les opérations futures.

    \b
    Stratégies d'échantillonnage :
      --all              Toutes les notes (défaut)
      --sample N         N notes aléatoires
      --percent P        P% de notes par dossier (stratifié)

    \b
    Exemples :
      obsillama scan                  # Toutes les notes avec cache
      obsillama scan --percent 15     # 15% par dossier
      obsillama scan --sample 100     # 100 notes aléatoires
      obsillama scan --force          # Forcer le re-scan
    """
    # Vérifier qu'on a une config
    if ctx.config is None:
        print_error(
            "Aucune configuration trouvée. "
            "Lancez d'abord 'obsillama init' pour initialiser le projet."
        )
        sys.exit(1)

    print_header("🔍 ObsIllama - Scan du vault")

    # ========================================================================
    # Étape 1 : Initialisation du scanner
    # ========================================================================
    print_step(1, 4, "Initialisation du scanner")

    try:
        scanner = NoteScanner()
        vault_path = scanner.vault_path
        print_success(f"Scanner initialisé : {vault_path}")
    except Exception as e:
        print_error(f"Erreur d'initialisation du scanner : {e}")
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 2 : Vérification du cache existant
    # ========================================================================
    print_step(2, 4, "Vérification du cache")

    cached_notes = None
    if not force:
        try:
            cached_notes = scanner.load_cache()
            if cached_notes:
                print_info(f"Cache trouvé : {len(cached_notes)} notes")

                if not scan_all and not sample and not percent:
                    # Si aucune option spécifiée et cache existe, proposer d'utiliser le cache
                    print_panel(
                        "Un cache existe déjà. Utilisez --force pour re-scanner.\n"
                        "Statistiques du cache :",
                        title="Cache existant",
                        border_style="yellow",
                    )

                    # Afficher les stats du cache
                    stats = compute_statistics(cached_notes)
                    print_stats(
                        {
                            "Notes": f"{stats['total_notes']:,}",
                            "Mots": f"{stats['total_words']:,}",
                            "Tags uniques": f"{stats['unique_tags']:,}",
                            "Dossiers": f"{stats['unique_folders']:,}",
                        },
                        title="Statistiques du cache",
                    )

                    console.print()
                    display_top_items(cached_notes, top_n=top)

                    print_success("Utilisez les notes en cache (ajoutez --force pour re-scanner)")
                    return
            else:
                print_info("Aucun cache trouvé, scan nécessaire")
        except Exception as e:
            print_warning(f"Erreur lors du chargement du cache : {e}")
            cached_notes = None
    else:
        print_info("Mode force : le cache sera ignoré")

    console.print()

    # ========================================================================
    # Étape 3 : Scan et parsing
    # ========================================================================
    print_step(3, 4, "Scan et parsing des notes")

    # Déterminer la stratégie
    if scan_all:
        strategy: Literal["all", "random", "stratified"] = "all"
        sample_size = None
        sample_percentage = None
        print_info("Stratégie : Toutes les notes")
    elif sample:
        strategy = "random"
        sample_size = sample
        sample_percentage = None
        print_info(f"Stratégie : Échantillonnage aléatoire ({sample} notes)")
    elif percent:
        strategy = "stratified"
        sample_size = None
        sample_percentage = percent
        print_info(f"Stratégie : Échantillonnage stratifié ({percent}%)")
    else:
        # Par défaut : toutes les notes
        strategy = "all"
        sample_size = None
        sample_percentage = None
        print_info("Stratégie : Toutes les notes (défaut)")

    console.print()

    try:
        # Scanner d'abord pour avoir le compte total
        print_info("Scan du vault en cours...")
        all_files = scanner.scan_vault()
        total_files = len(all_files)

        print_success(f"{total_files:,} fichiers .md trouvés")
        console.print()

        # Parser les notes
        print_info("Parsing des notes...")
        notes = scanner.scan_and_parse(
            strategy=strategy,
            sample_size=sample_size,
            sample_percentage=sample_percentage,
        )

        if not notes:
            print_warning("Aucune note n'a pu être parsée")
            sys.exit(0)

        print_success(f"{len(notes):,} notes parsées avec succès")

    except Exception as e:
        print_error(f"Erreur lors du scan : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 4 : Sauvegarde du cache
    # ========================================================================
    print_step(4, 4, "Sauvegarde du cache")

    if no_cache:
        print_info("Cache désactivé (--no-cache)")
    else:
        try:
            scanner.save_cache(notes)
            cache_path = scanner.cache_path
            print_success(f"Cache sauvegardé : {cache_path}")
        except Exception as e:
            print_warning(f"Erreur lors de la sauvegarde du cache : {e}")

    console.print()

    # ========================================================================
    # Statistiques
    # ========================================================================
    print_header("📊 Statistiques du vault")

    stats = compute_statistics(notes)

    print_stats(
        {
            "Total notes": f"{stats['total_notes']:,}",
            "Total mots": f"{stats['total_words']:,}",
            "Mots/note (moy)": f"{stats['avg_words']:,}",
            "Tags uniques": f"{stats['unique_tags']:,}",
            "Total tags": f"{stats['total_tags']:,}",
            "Backlinks (moy)": f"{stats['avg_backlinks']}",
            "Dossiers": f"{stats['unique_folders']:,}",
            "Notes avec tags": f"{stats['notes_with_tags']:,}",
            "Notes sans tags": f"{stats['notes_without_tags']:,}",
        },
        title="Statistiques générales",
    )

    console.print()

    # Afficher les tops
    display_top_items(notes, top_n=top)

    # ========================================================================
    # Résumé et prochaines étapes
    # ========================================================================
    print_summary(
        title="✓ Scan terminé",
        items=[
            f"{len(notes):,} notes parsées",
            f"Cache sauvegardé" if not no_cache else "Cache non sauvegardé",
            f"{stats['total_words']:,} mots au total",
            f"{stats['unique_tags']:,} tags uniques",
        ],
        border_style="green",
    )

    console.print()

    print_panel(
        "Prochaines étapes :\n"
        "  1. obsillama analyze       # Analyser et catégoriser\n"
        "  2. obsillama review        # Réviser les catégories\n"
        "  3. obsillama embed         # Générer les embeddings",
        title="🚀 Suite du workflow",
        border_style="cyan",
    )
