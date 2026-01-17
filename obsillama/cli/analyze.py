"""
ObsIllama - Commande analyze

Cette commande exécute le pipeline GraphRAG et génère les catégories.
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import click

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.note_scanner import NoteScanner
from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.graphrag_integration import GraphRAGPipeline
from obsillama.core.category_generator import CategoryGenerator
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.storage.graph_store import GraphStore
from obsillama.storage.category_store import CategoryStore
from obsillama.models.note import Note
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
    console,
)


@click.command()
@click.option(
    "--categories",
    type=int,
    help="Nombre de catégories cibles (défaut: depuis config)",
)
@click.option(
    "--min-notes",
    type=int,
    help="Minimum de notes par catégorie (défaut: depuis config)",
)
@click.option(
    "--min-community-size",
    type=int,
    help="Taille minimum d'une communauté GraphRAG (défaut: depuis config)",
)
@click.option(
    "--no-progress",
    is_flag=True,
    help="Désactiver les barres de progression",
)
@pass_context
def analyze(
    ctx: ObsillamaContext,
    categories: Optional[int],
    min_notes: Optional[int],
    min_community_size: Optional[int],
    no_progress: bool,
):
    """
    Analyse le vault avec GraphRAG et génère les catégories.

    Cette commande exécute :
      • GraphRAG : extraction entités, relations, communautés
      • Génération de catégories à partir des communautés
      • Assignation des notes aux catégories
      • Sauvegarde dans LanceDB et JSON

    \b
    Prérequis :
      Vous devez d'abord scanner le vault avec 'obsillama scan'

    \b
    Exemples :
      obsillama analyze                      # Avec config par défaut
      obsillama analyze --categories 15      # 15 catégories cibles
      obsillama analyze --min-community-size 5  # Communautés de 5+ entités
    """
    # Vérifier qu'on a une config
    if ctx.config is None:
        print_error(
            "Aucune configuration trouvée. "
            "Lancez d'abord 'obsillama init' pour initialiser le projet."
        )
        sys.exit(1)

    print_header("🧠 ObsIllama - Analyse GraphRAG")

    # ========================================================================
    # Étape 1 : Chargement des notes depuis le cache
    # ========================================================================
    print_step(1, 6, "Chargement des notes depuis le cache")

    try:
        scanner = NoteScanner()
        notes = scanner.load_cache()

        if not notes:
            print_error(
                "Aucun cache de notes trouvé. "
                "Lancez d'abord 'obsillama scan' pour scanner le vault."
            )
            sys.exit(1)

        print_success(f"{len(notes):,} notes chargées depuis le cache")

    except Exception as e:
        print_error(f"Erreur lors du chargement du cache : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 2 : Initialisation des composants
    # ========================================================================
    print_step(2, 6, "Initialisation des composants")

    try:
        # Ollama client
        print_info("Initialisation du client Ollama...")
        ollama_client = OllamaClient()

        # GraphRAG Pipeline
        min_comm_size = min_community_size or ctx.config.graphrag.min_community_size
        num_workers = ctx.config.processing.num_workers
        print_info(
            f"Configuration GraphRAG (min_community_size={min_comm_size}, "
            f"workers={num_workers})..."
        )
        graphrag_pipeline = GraphRAGPipeline(
            ollama_client=ollama_client,
            min_community_size=min_comm_size,
            leiden_resolution=ctx.config.graphrag.resolution,
            max_workers=num_workers,
        )

        # Category Generator
        target_cats = categories or ctx.config.categorization.target_count
        min_notes_cat = min_notes or ctx.config.categorization.min_notes_per_category
        print_info(
            f"Configuration Catégorisation (target={target_cats}, min_notes={min_notes_cat})..."
        )
        category_generator = CategoryGenerator(
            ollama_client=ollama_client,
            target_category_count=target_cats,
            min_notes_per_category=min_notes_cat,
            confidence_threshold=ctx.config.categorization.thresholds.assignment_confidence,
        )

        # Embedding Manager
        print_info("Initialisation du gestionnaire d'embeddings...")
        embedding_manager = EmbeddingManager(ollama_client=ollama_client)

        # Stores
        print_info("Initialisation des stores de données...")
        graph_store = GraphStore()
        category_store = CategoryStore()

        print_success("Tous les composants sont initialisés")

    except Exception as e:
        print_error(f"Erreur d'initialisation : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 3 : Exécution du pipeline GraphRAG
    # ========================================================================
    print_step(3, 6, "Exécution du pipeline GraphRAG")

    print_panel(
        "Cette étape peut prendre plusieurs minutes...\n\n"
        "Le pipeline va :\n"
        "  • Extraire les entités de chaque note via LLM\n"
        "  • Détecter les relations entre entités\n"
        "  • Construire un graphe de connaissances\n"
        "  • Détecter les communautés avec Leiden\n"
        "  • Générer des résumés de communautés",
        title="Pipeline GraphRAG",
        border_style="cyan",
    )

    console.print()

    try:
        entities, relationships, communities = graphrag_pipeline.run_full_pipeline(
            notes, show_progress=not no_progress
        )

        print_success(f"Pipeline GraphRAG terminé")
        print_info(f"  → {len(entities):,} entités extraites")
        print_info(f"  → {len(relationships):,} relations détectées")
        print_info(f"  → {len(communities):,} communautés trouvées")

        # Générer embeddings pour entités et communautés
        print_info("Génération des embeddings pour le graphe...")

        # Embeddings des entités (nom + description)
        entity_texts = [f"{e.name}: {e.description}" for e in entities]
        entity_embeddings = embedding_manager.generate_embeddings_batch(
            entity_texts, show_progress=False
        )

        # Embeddings des communautés (résumé)
        community_texts = [c.description for c in communities] if communities else []
        community_embeddings = (
            embedding_manager.generate_embeddings_batch(
                community_texts, show_progress=False
            )
            if community_texts
            else []
        )

        print_success(f"Embeddings générés ({len(entity_embeddings)} entités, {len(community_embeddings)} communautés)")

        # Sauvegarder dans LanceDB
        print_info("Sauvegarde dans LanceDB...")
        graph_store.save_graph(entities, relationships, communities, entity_embeddings, community_embeddings)
        print_success("Graphe sauvegardé dans LanceDB")

    except Exception as e:
        print_error(f"Erreur lors de l'exécution GraphRAG : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 4 : Génération des catégories
    # ========================================================================
    print_step(4, 6, "Génération des catégories")

    # Vérifier si on a des communautés
    if not communities:
        print_warning(
            "Aucune communauté n'a été détectée par GraphRAG.\n"
            "Cela peut arriver si :\n"
            "  • Le graphe est trop petit (peu de notes scannées)\n"
            "  • Le graphe est peu connecté (peu de relations entre entités)\n"
            "  • Le paramètre --min-community-size est trop élevé\n\n"
            "Solutions :\n"
            "  1. Scannez plus de notes : obsillama scan --percent 20\n"
            "  2. Réduisez --min-community-size : obsillama analyze --min-community-size 1"
        )
        console.print()
        print_panel(
            f"Graphe généré :\n"
            f"  • {len(entities)} entités extraites\n"
            f"  • {len(relationships)} relations détectées\n"
            f"  • 0 communautés (graphe trop petit/peu connecté)\n\n"
            "Le graphe a été sauvegardé dans LanceDB.\n"
            "Re-lancez l'analyse avec plus de notes.",
            title="⚠️  Analyse incomplète",
            border_style="yellow",
        )
        sys.exit(1)

    try:
        print_info(
            f"Génération de catégories depuis {len(communities)} communautés..."
        )
        categories_list = category_generator.generate_from_communities(
            communities, entities
        )

        if not categories_list:
            print_warning(
                "Aucune catégorie n'a pu être générée. "
                "Essayez de réduire --min-community-size ou scannez plus de notes."
            )
            sys.exit(0)

        print_success(f"{len(categories_list)} catégories générées")

        # Sauvegarder la taxonomie
        print_info("Sauvegarde de la taxonomie...")
        category_store.save_taxonomy(categories_list)
        print_success("Taxonomie sauvegardée")

    except Exception as e:
        print_error(f"Erreur lors de la génération des catégories : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 5 : Génération des embeddings
    # ========================================================================
    print_step(5, 6, "Génération des embeddings")

    try:
        # Embeddings des notes
        print_info(f"Génération des embeddings pour {len(notes)} notes...")

        # Préparer les textes (titre + contenu)
        # Tronquer à 6000 caractères pour éviter de dépasser la limite du modèle (~8192 tokens)
        max_chars = 6000
        note_texts = []
        truncated_count = 0
        for note in notes:
            full_text = f"{note.title}\n\n{note.content}"
            if len(full_text) > max_chars:
                truncated_text = full_text[:max_chars] + "..."
                note_texts.append(truncated_text)
                truncated_count += 1
            else:
                note_texts.append(full_text)

        if truncated_count > 0:
            print_warning(
                f"{truncated_count} notes tronquées à {max_chars} caractères "
                f"(limite du modèle d'embedding)"
            )

        # Générer les embeddings
        note_embeddings = embedding_manager.generate_embeddings_batch(
            note_texts, batch_size=32, show_progress=not no_progress
        )

        if len(note_embeddings) != len(notes):
            print_warning(
                f"Seulement {len(note_embeddings)}/{len(notes)} notes ont des embeddings"
            )

        print_success(f"{len(note_embeddings)} embeddings de notes générés")

        # Mettre à jour les métadonnées des notes
        notes_with_embeddings = []
        for note in notes:
            note_dict = note.model_dump()
            note_dict["has_embedding"] = True
            note_dict["embedding_model"] = embedding_manager.model_name
            note_dict["embedding_date"] = datetime.now()
            updated_note = Note(**note_dict)
            notes_with_embeddings.append(updated_note)

        # Embeddings des catégories (description)
        print_info(f"Génération des embeddings pour {len(categories_list)} catégories...")
        category_texts = [
            f"{cat.name}: {cat.description}" for cat in categories_list
        ]

        category_embeddings = embedding_manager.generate_embeddings_batch(
            category_texts, show_progress=not no_progress
        )

        print_success(f"{len(category_embeddings)} embeddings de catégories générés")

    except Exception as e:
        print_error(f"Erreur lors de la génération des embeddings : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 6 : Assignation des notes aux catégories
    # ========================================================================
    print_step(6, 6, "Assignation des notes aux catégories")

    try:
        print_info("Calcul des similarités et assignation...")
        assignments = category_generator.assign_notes_to_categories(
            notes=notes_with_embeddings,
            categories=categories_list,
            note_embeddings=note_embeddings,
            category_embeddings=category_embeddings,
        )

        # Statistiques
        total_assigned = sum(len(note_list) for note_list in assignments.values())
        coverage = (total_assigned / len(notes)) * 100 if notes else 0

        print_success(f"{total_assigned}/{len(notes)} notes assignées ({coverage:.1f}% couverture)")

        # Sauvegarder les assignations
        print_info("Sauvegarde des assignations...")
        category_store.save_assignments(assignments)
        print_success("Assignations sauvegardées")

    except Exception as e:
        print_error(f"Erreur lors de l'assignation : {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    console.print()

    # ========================================================================
    # Résumé et statistiques
    # ========================================================================
    print_header("📊 Résumé de l'analyse")

    print_stats(
        {
            "Notes analysées": f"{len(notes):,}",
            "Entités extraites": f"{len(entities):,}",
            "Relations détectées": f"{len(relationships):,}",
            "Communautés trouvées": f"{len(communities):,}",
            "Catégories générées": f"{len(categories_list):,}",
            "Notes assignées": f"{total_assigned:,}",
            "Couverture": f"{coverage:.1f}%",
        },
        title="Statistiques de l'analyse",
    )

    console.print()

    # Top catégories par nombre de notes
    cat_sizes = [(cat.name, len(assignments.get(cat.id, []))) for cat in categories_list]
    cat_sizes.sort(key=lambda x: x[1], reverse=True)

    if cat_sizes:
        print_table(
            title=f"Top {min(10, len(cat_sizes))} Catégories",
            columns=[
                {"name": "Catégorie", "style": "cyan"},
                {"name": "Notes", "justify": "right", "style": "green"},
            ],
            rows=[[name, str(count)] for name, count in cat_sizes[:10]],
        )

    console.print()

    # ========================================================================
    # Résumé final
    # ========================================================================
    print_summary(
        title="✓ Analyse terminée",
        items=[
            f"{len(entities):,} entités GraphRAG",
            f"{len(communities):,} communautés détectées",
            f"{len(categories_list):,} catégories générées",
            f"{total_assigned:,} notes assignées ({coverage:.1f}%)",
            "Données sauvegardées dans LanceDB et JSON",
        ],
        border_style="green",
    )

    console.print()

    print_panel(
        "Prochaines étapes :\n"
        "  1. obsillama review        # Réviser les catégories\n"
        "  2. obsillama embed         # Générer tous les embeddings\n"
        "  3. obsillama apply         # Appliquer au vault",
        title="🚀 Suite du workflow",
        border_style="cyan",
    )
