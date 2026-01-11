"""
ObsIllama - Commande embed

Cette commande génère les embeddings vectoriels pour toutes les notes du vault
et les stocke dans LanceDB pour permettre la recherche sémantique.
"""

import sys
import time
from pathlib import Path
from typing import Optional

import click

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.note_scanner import NoteScanner
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
    print_step,
    print_stats,
    print_panel,
    console,
)


@click.command()
@click.option(
    "--batch-size",
    type=int,
    default=32,
    help="Taille des batchs pour génération d'embeddings (défaut: 32)",
)
@click.option(
    "--force-recompute",
    is_flag=True,
    help="Forcer le recalcul de tous les embeddings (ignore le cache)",
)
@click.option(
    "--scan-all",
    is_flag=True,
    help="Scanner toutes les notes du vault (au lieu d'utiliser le cache de scan)",
)
@pass_context
def embed(
    ctx: ObsillamaContext,
    batch_size: int,
    force_recompute: bool,
    scan_all: bool,
):
    """
    Génère les embeddings vectoriels pour les notes et les stocke dans LanceDB.

    Cette commande:
    1. Charge les notes (depuis cache ou vault complet)
    2. Génère les embeddings par batch avec le modèle configuré
    3. Sauvegarde les embeddings dans LanceDB
    4. Affiche les statistiques de performance

    Exemples:
        obsillama embed
        obsillama embed --batch-size 64
        obsillama embed --force-recompute
        obsillama embed --scan-all --batch-size 16
    """
    # En-tête
    print_header("🧠 Génération des Embeddings Vectoriels")
    print_info("Cette commande encode vos notes en vecteurs sémantiques")
    console.print()

    config = ctx.config

    # Étape 1/5 : Chargement des notes
    print_step(1, 5, "Chargement des notes")

    try:
        vault_path = Path(config.vault.path)
        cache_dir = Path("data/cache")
        cache_file = cache_dir / "scanned_notes.json"

        # Initialiser le scanner
        scanner = NoteScanner(
            vault_path=vault_path,
            exclude_folders=config.vault.exclude_folders,
            cache_path=cache_file,
        )

        # Charger les notes
        if scan_all:
            print_info("Scan complet du vault demandé...")
            notes = scanner.scan_and_parse(
                sample_strategy="all",
                sample_size=None,
            )
        elif cache_file.exists():
            print_info(f"Chargement depuis le cache: {cache_file}")
            notes = scanner.load_cache()
        else:
            print_warning(
                "Aucun cache de notes trouvé. Utilisez --scan-all ou "
                "exécutez d'abord 'obsillama scan'."
            )
            sys.exit(1)

        if not notes:
            print_error("Aucune note trouvée à traiter")
            sys.exit(1)

        print_success(f"{len(notes)} notes chargées avec succès")

    except Exception as e:
        print_error(f"Erreur lors du chargement des notes: {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    # Étape 2/5 : Initialisation des composants
    print_step(2, 5, "Initialisation des composants")

    try:
        # Client Ollama
        ollama_client = OllamaClient(
            base_url=config.ollama.base_url,
            generation_model=config.ollama.models.generation,
            embedding_model=config.ollama.models.embedding,
        )

        # EmbeddingManager avec cache
        cache_path = Path("data/cache") / "embeddings_cache.json"
        embedding_manager = EmbeddingManager(
            ollama_client=ollama_client,
            cache_path=cache_path,
            model_name=config.ollama.models.embedding,
            model_dimension=768,  # nomic-embed-text = 768 dims
        )

        # LanceDB et EmbeddingStore
        lancedb_path = Path(config.lancedb.path)
        db_manager = LanceDBManager(db_path=lancedb_path)
        embedding_store = EmbeddingStore(lancedb_manager=db_manager)

        print_success("Tous les composants initialisés")

        # Afficher les stats du cache si disponible
        if not force_recompute:
            cache_stats = embedding_manager.get_cache_stats()
            print_info(
                f"Cache d'embeddings: {cache_stats['cache_size']} entrées"
            )

    except Exception as e:
        print_error(f"Erreur lors de l'initialisation: {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    # Étape 3/5 : Génération des embeddings
    print_step(3, 5, "Génération des embeddings")
    print_info(f"Traitement par batch de {batch_size} notes")

    try:
        start_time = time.time()

        # Options de génération
        use_cache = not force_recompute

        if force_recompute:
            print_warning("Mode force-recompute activé : le cache sera ignoré")

        # Générer les embeddings pour toutes les notes
        updated_notes = embedding_manager.embed_notes(
            notes=notes,
            batch_size=batch_size,
            use_cache=use_cache,
            show_progress=True,
            max_length=2000,
        )

        # Extraire les embeddings (ils sont en cache mais pas dans les objets Note)
        embeddings = []
        for note in updated_notes:
            # Reconstruire le texte de la note pour récupérer l'embedding du cache
            text = f"{note.title}\n\n{note.content}"
            if len(text) > 2000:
                text = text[:2000]

            # Récupérer depuis le cache
            content_hash = embedding_manager._compute_content_hash(text)
            embedding = embedding_manager._cache.get(content_hash)

            if embedding is None:
                print_error(f"Embedding manquant pour note: {note.title}")
                sys.exit(1)

            embeddings.append(embedding)

        end_time = time.time()
        elapsed_time = end_time - start_time

        print_success(
            f"{len(embeddings)} embeddings générés en "
            f"{elapsed_time:.1f}s ({len(notes) / elapsed_time:.1f} notes/sec)"
        )

    except Exception as e:
        print_error(f"Erreur lors de la génération des embeddings: {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    # Étape 4/5 : Sauvegarde dans LanceDB
    print_step(4, 5, "Sauvegarde dans LanceDB")

    try:
        # Upsert des embeddings dans LanceDB
        embedding_store.upsert_embeddings(
            notes=updated_notes,
            embeddings=embeddings,
        )

        print_success("Embeddings sauvegardés dans LanceDB")

    except Exception as e:
        print_error(f"Erreur lors de la sauvegarde dans LanceDB: {e}")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)

    # Étape 5/5 : Statistiques et résumé
    print_step(5, 5, "Statistiques et résumé")

    try:
        # Stats de l'EmbeddingStore
        store_stats = embedding_store.get_embedding_stats()

        # Stats du cache
        cache_stats = embedding_manager.get_cache_stats()

        # Afficher les statistiques
        stats_data = {
            "Notes encodées": len(notes),
            "Temps total": f"{elapsed_time:.1f}s",
            "Vitesse": f"{len(notes) / elapsed_time:.1f} notes/sec",
            "Batch size": batch_size,
            "Notes en DB": store_stats["notes_with_embeddings"],
            "Cache size": cache_stats["cache_size"],
            "Modèle": cache_stats["model_name"],
            "Dimension": cache_stats["model_dimension"],
        }

        print_stats(stats_data)

        print_success("✅ Génération d'embeddings terminée avec succès")

    except Exception as e:
        print_error(f"Erreur lors du calcul des statistiques: {e}")
        if ctx.verbose:
            console.print_exception()

    # Prochaines étapes
    print_panel(
        "Prochaines étapes:\n\n"
        "1. obsillama query \"votre recherche\"  # Rechercher dans vos notes\n"
        "2. obsillama apply                      # Appliquer les catégories au vault\n"
        "3. obsillama stats                      # Voir les statistiques complètes",
        title="🚀 Suite du workflow",
        border_style="cyan",
    )
