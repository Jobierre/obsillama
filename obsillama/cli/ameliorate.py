"""
ObsIllama - Commande ameliorate

Cette commande améliore incrémentalement la taxonomie existante en assignant
les nouvelles notes aux catégories et en suggérant des améliorations.
"""

import sys
from pathlib import Path
from typing import List

import click

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.note_scanner import NoteScanner
from obsillama.core.category_ameliorator import CategoryAmeliorator
from obsillama.storage.category_store import CategoryStore
from obsillama.llm.ollama_client import OllamaClient
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.utils.progress import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_step,
    print_stats,
    print_panel,
    print_table,
    confirm,
    console,
)


@click.command()
@click.option(
    "--new-only",
    is_flag=True,
    help="Traiter uniquement les nouvelles notes (non dans le cache)",
)
@click.option(
    "--refine",
    is_flag=True,
    help="Raffiner les catégories existantes (recalcul centroides)",
)
@click.option(
    "--subcats",
    is_flag=True,
    help="Suggérer des sous-catégories via clustering",
)
@click.option(
    "--merge-threshold",
    type=float,
    default=0.85,
    help="Seuil de similarité pour suggérer fusions (défaut: 0.85)",
)
@click.option(
    "--confidence",
    type=float,
    default=0.7,
    help="Seuil minimum de confiance pour assignation (défaut: 0.7)",
)
@pass_context
def ameliorate(
    ctx: ObsillamaContext,
    new_only: bool,
    refine: bool,
    subcats: bool,
    merge_threshold: float,
    confidence: float,
):
    """
    Améliore incrémentalement la taxonomie existante.

    Cette commande:
    1. Détecte les nouvelles notes (ou notes modifiées)
    2. Assigne les nouvelles notes aux catégories existantes (K-NN)
    3. Raffine les catégories (recalcul centroides, stats)
    4. Suggère des sous-catégories (clustering intra-catégorie)
    5. Suggère des fusions (catégories trop similaires)

    Options:
        --new-only : Traiter uniquement les notes nouvelles/modifiées
        --refine : Raffiner les catégories existantes
        --subcats : Suggérer des sous-catégories
        --merge-threshold : Seuil pour fusions (0-1, défaut: 0.85)

    Exemples:
        obsillama ameliorate --new-only
        obsillama ameliorate --refine --subcats
        obsillama ameliorate --merge-threshold 0.9
    """
    # En-tête
    print_header("🔄 Amélioration Incrémentale de la Taxonomie")
    print_info("Assignation des nouvelles notes et suggestions d'amélioration")
    console.print()

    # ========================================================================
    # Étape 1 : Détection des nouvelles notes
    # ========================================================================
    print_step(1, 5, "Détection des changements")

    try:
        # Scanner
        scanner = NoteScanner()

        # Charger le cache
        cached_notes = scanner.load_cache()

        if not cached_notes:
            print_error("Aucun cache trouvé. Lancez d'abord 'obsillama scan'")
            sys.exit(1)

        # Détecter les changements
        if new_only:
            new_files = scanner.detect_new_notes(cached_notes)
            modified_files = scanner.detect_modified_notes(cached_notes)
            deleted_notes = scanner.detect_deleted_notes(cached_notes)

            total_changes = len(new_files) + len(modified_files) + len(deleted_notes)

            print_stats({
                "Nouvelles notes": len(new_files),
                "Notes modifiées": len(modified_files),
                "Notes supprimées": len(deleted_notes),
                "Total changements": total_changes,
            })

            if total_changes == 0:
                print_success("Aucun changement détecté !")
                print_info("Toutes les notes sont à jour.")
                sys.exit(0)

            # Parser les nouvelles et modifiées
            files_to_process = new_files + modified_files
            new_notes = []

            for file_path in files_to_process:
                try:
                    note = scanner.parse_note(file_path)
                    new_notes.append(note)
                except Exception as e:
                    print_warning(f"Erreur sur {file_path.name}: {e}")

        else:
            # Traiter toutes les notes
            new_notes = cached_notes
            print_info(f"Mode complet : {len(new_notes)} notes à traiter")

    except Exception as e:
        print_error(f"Erreur lors de la détection : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 2 : Initialisation du CategoryAmeliorator
    # ========================================================================
    print_step(2, 5, "Initialisation du système")

    try:
        # Clients
        ollama_client = OllamaClient()
        category_store = CategoryStore()
        embedding_manager = EmbeddingManager(ollama_client=ollama_client)

        # Ameliorator
        ameliorator = CategoryAmeliorator(
            category_store=category_store,
            embedding_manager=embedding_manager,
            ollama_client=ollama_client,
            confidence_threshold=confidence,
        )

        print_success("Système initialisé")

    except Exception as e:
        print_error(f"Erreur lors de l'initialisation : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 3 : Amélioration de la taxonomie
    # ========================================================================
    print_step(3, 5, "Amélioration de la taxonomie")

    try:
        result = ameliorator.run_amelioration(
            new_notes=new_notes,
            suggest_subcats=subcats,
            suggest_fusions=True,
            merge_threshold=merge_threshold,
        )

        print_success("Amélioration terminée")

    except ValueError as e:
        print_error(str(e))
        print_panel(
            "Lancez d'abord 'obsillama analyze' pour créer une taxonomie initiale.",
            title="⚠️  Aucune taxonomie existante",
            border_style="yellow",
        )
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur lors de l'amélioration : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 4 : Affichage des résultats
    # ========================================================================
    print_step(4, 5, "Résultats de l'amélioration")

    # Statistiques
    print_stats({
        "Nouvelles notes": result["new_notes_count"],
        "Notes assignées": result["assigned_notes_count"],
        "Couverture": f"{result['coverage_percent']:.1f}%",
        "Catégories": result["categories_count"],
        "Catégories mises à jour": result["categories_with_new_notes"],
    })

    console.print()

    # Sous-catégories suggérées
    if subcats and result["subcategory_suggestions"]:
        print_info(f"💡 {len(result['subcategory_suggestions'])} sous-catégories suggérées :")

        subcat_data = []
        for subcat in result["subcategory_suggestions"][:10]:  # Limiter à 10
            subcat_data.append([
                subcat.name,
                f"{subcat.note_count} notes",
                subcat.review_status.value,
            ])

        print_table(
            title="Sous-catégories Suggérées",
            columns=[
                {"name": "Nom", "style": "cyan"},
                {"name": "Notes", "justify": "right"},
                {"name": "Statut", "style": "yellow"},
            ],
            rows=subcat_data,
        )

        console.print()

    # Fusions suggérées
    if result["merge_suggestions"]:
        print_info(f"🔗 {len(result['merge_suggestions'])} fusions suggérées :")

        merge_data = []
        for cat1_id, cat2_id, similarity in result["merge_suggestions"][:10]:
            merge_data.append([
                cat1_id[:8],
                cat2_id[:8],
                f"{similarity:.2f}",
            ])

        print_table(
            title="Fusions Suggérées",
            columns=[
                {"name": "Catégorie 1", "style": "cyan"},
                {"name": "Catégorie 2", "style": "cyan"},
                {"name": "Similarité", "justify": "right", "style": "green"},
            ],
            rows=merge_data,
        )

        console.print()

    # ========================================================================
    # Étape 5 : Résumé
    # ========================================================================
    print_step(5, 5, "Résumé")

    print_panel(
        f"✅ {result['assigned_notes_count']} nouvelles notes assignées\n"
        f"📊 {result['categories_with_new_notes']} catégories mises à jour\n"
        f"💡 {len(result['subcategory_suggestions'])} sous-catégories suggérées\n"
        f"🔗 {len(result['merge_suggestions'])} fusions suggérées",
        title="🎯 Amélioration Terminée",
        border_style="green",
    )

    console.print()

    print_info("Prochaines étapes:")
    console.print(f"  1. Reviewez les suggestions: [cyan]obsillama review --interactive[/]")
    console.print(f"  2. Appliquez les catégories: [cyan]obsillama apply[/]")
    console.print()
