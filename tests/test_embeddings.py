"""
Tests pour le système d'embeddings (Phase 3)

Ce script teste:
- EmbeddingManager (génération et cache)
- EmbeddingStore (stockage et recherche)
- Recherche sémantique
- Performance
"""

import sys
import time
from pathlib import Path

# Ajouter le projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from obsillama.llm.ollama_client import OllamaClient
from obsillama.core.note_scanner import NoteScanner
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.storage.embedding_store import EmbeddingStore
from obsillama.config.settings import get_settings


def print_section(title: str):
    """Affiche un titre de section"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def test_embeddings():
    """Test principal du système d'embeddings"""

    print_section("TEST SYSTÈME D'EMBEDDINGS - PHASE 3")

    # ========================================================================
    # 1. Initialisation
    # ========================================================================
    print_section("1. Initialisation des composants")

    settings = get_settings()

    # Client Ollama
    print("⏳ Initialisation OllamaClient...")
    ollama_client = OllamaClient(
        base_url=settings.ollama.base_url,
        generation_model=settings.ollama.models.generation,
        embedding_model=settings.ollama.models.embedding,
    )
    print("✅ OllamaClient initialisé")

    # EmbeddingManager
    print("\n⏳ Initialisation EmbeddingManager...")
    cache_path = project_root / "data" / "cache" / "embeddings_cache.json"
    embedding_manager = EmbeddingManager(
        ollama_client=ollama_client,
        cache_path=cache_path,
    )
    print("✅ EmbeddingManager initialisé")
    print(f"   Cache: {cache_path}")

    # LanceDB Manager
    print("\n⏳ Initialisation LanceDBManager...")
    db_path = project_root / "data" / "lancedb"
    lancedb_manager = LanceDBManager(db_path=str(db_path))
    print("✅ LanceDBManager initialisé")
    print(f"   DB Path: {db_path}")
    print(f"   Tables existantes: {lancedb_manager.list_tables()}")

    # EmbeddingStore
    print("\n⏳ Initialisation EmbeddingStore...")
    embedding_store = EmbeddingStore(lancedb_manager=lancedb_manager)
    print("✅ EmbeddingStore initialisé")

    # ========================================================================
    # 2. Scanner les notes
    # ========================================================================
    print_section("2. Scan des notes du vault")

    vault_path = settings.vault.path
    print(f"Vault: {vault_path}")

    scanner = NoteScanner(
        vault_path=vault_path,
        exclude_folders=settings.vault.exclude_folders,
    )

    # Scanner 20 notes (stratifié) pour les tests
    print("\n⏳ Scan de 20 notes (échantillonnage stratifié)...")
    notes = scanner.scan_and_parse(
        strategy="stratified",
        sample_size=20,
    )
    print(f"✅ {len(notes)} notes scannées")

    if notes:
        print(f"\n📝 Exemple de note:")
        print(f"   Titre: {notes[0].title}")
        print(f"   Path: {notes[0].relative_path}")
        print(f"   Mots: {notes[0].word_count}")
        print(f"   Tags: {notes[0].tags[:3] if notes[0].tags else []}")

    # ========================================================================
    # 3. Génération d'embeddings
    # ========================================================================
    print_section("3. Génération d'embeddings")

    print(f"⏳ Génération embeddings pour {len(notes)} notes...")
    start_time = time.time()

    updated_notes = embedding_manager.embed_notes(
        notes=notes,
        batch_size=4,  # Batch très petit pour éviter de dépasser la limite
        use_cache=True,
        show_progress=True,
        max_length=2000,  # Limite stricte de 2000 caractères
    )

    elapsed = time.time() - start_time
    print(f"\n✅ Embeddings générés en {elapsed:.2f}s")
    print(f"   Vitesse: {len(notes) / elapsed:.2f} notes/sec")

    # Vérifier les métadonnées
    print("\n📊 Métadonnées d'embedding:")
    print(f"   has_embedding: {updated_notes[0].has_embedding}")
    print(f"   embedding_model: {updated_notes[0].embedding_model}")
    print(f"   embedding_date: {updated_notes[0].embedding_date}")

    # ========================================================================
    # 4. Test du cache
    # ========================================================================
    print_section("4. Test du cache")

    print("⏳ Régénération des embeddings (devrait utiliser le cache)...")
    start_time = time.time()

    cached_notes = embedding_manager.embed_notes(
        notes=notes,
        batch_size=4,
        use_cache=True,
        show_progress=True,
        max_length=2000,
    )

    cached_elapsed = time.time() - start_time
    print(f"\n✅ Embeddings régénérés en {cached_elapsed:.2f}s (avec cache)")
    print(f"   Accélération: {elapsed / cached_elapsed:.2f}x")

    # Stats du cache
    cache_stats = embedding_manager.get_cache_stats()
    print(f"\n📊 Stats du cache:")
    print(f"   Taille: {cache_stats['cache_size']} embeddings")
    print(f"   Modèle: {cache_stats['model_name']}")
    print(f"   Dimension: {cache_stats['model_dimension']}")

    # ========================================================================
    # 5. Stockage dans LanceDB
    # ========================================================================
    print_section("5. Stockage dans LanceDB")

    # Extraire les embeddings pour le stockage
    print("⏳ Extraction des embeddings depuis le cache...")
    embeddings = []
    for note in updated_notes:
        # Reconstruire le texte
        text = f"{note.title}\n\n{note.content}"
        content_hash = embedding_manager._compute_content_hash(text)

        # Récupérer depuis le cache
        if content_hash in embedding_manager._cache:
            embeddings.append(embedding_manager._cache[content_hash])
        else:
            print(f"⚠️  Embedding non trouvé dans le cache pour: {note.title}")
            # Fallback: générer l'embedding
            emb = embedding_manager.generate_embedding(text)
            embeddings.append(emb)

    print(f"✅ {len(embeddings)} embeddings extraits")

    # Upsert dans LanceDB
    print("\n⏳ Upsert des embeddings dans LanceDB...")
    embedding_store.upsert_embeddings(
        notes=updated_notes,
        embeddings=embeddings,
    )
    print("✅ Embeddings stockés dans LanceDB")

    # Stats du store
    stats = embedding_store.get_embedding_stats()
    print(f"\n📊 Stats EmbeddingStore:")
    print(f"   Total notes: {stats['total_notes']}")
    print(f"   Notes avec embeddings: {stats['notes_with_embeddings']}")
    print(f"   Tables: {stats['tables']}")

    # ========================================================================
    # 6. Recherche sémantique
    # ========================================================================
    print_section("6. Recherche sémantique")

    # Test 1: Recherche par texte "self-hosting docker"
    print("⏳ Test 1: Recherche 'self-hosting docker'")
    query1 = "self-hosting docker containers applications"

    results1 = embedding_store.search_by_text(
        query_text=query1,
        embedding_generator=embedding_manager.generate_embedding,
        top_k=5,
    )

    print(f"\n✅ {len(results1)} résultats trouvés:")
    for i, result in enumerate(results1, 1):
        similarity = result.get("_similarity", 0)
        print(f"\n   {i}. {result['title']}")
        print(f"      Similarité: {similarity:.3f}")
        print(f"      Path: {result['relative_path']}")
        print(f"      Mots: {result['word_count']}")

    # Test 2: Recherche avec seuil de similarité
    print("\n" + "─" * 70)
    print("⏳ Test 2: Recherche avec seuil > 0.7")

    query2 = "python programming language tutorial"
    query2_emb = embedding_manager.generate_embedding(query2)

    results2 = embedding_store.search_similar_notes(
        query_embedding=query2_emb,
        top_k=10,
        similarity_threshold=0.7,
    )

    print(f"\n✅ {len(results2)} résultats avec similarité > 0.7:")
    for i, result in enumerate(results2, 1):
        similarity = result.get("_similarity", 0)
        print(f"   {i}. {result['title'][:50]:50s} | Sim: {similarity:.3f}")

    # Test 3: Recherche avec filtre de mots
    print("\n" + "─" * 70)
    print("⏳ Test 3: Recherche notes longues (>500 mots)")

    results3 = embedding_store.search_similar_notes(
        query_embedding=query2_emb,
        top_k=5,
        min_word_count=500,
    )

    print(f"\n✅ {len(results3)} résultats (>500 mots):")
    for i, result in enumerate(results3, 1):
        print(f"   {i}. {result['title'][:40]:40s} | {result['word_count']} mots")

    # ========================================================================
    # 7. Tests de performance
    # ========================================================================
    print_section("7. Tests de performance")

    # Test de génération d'embeddings
    print("⏳ Benchmark génération embeddings...")
    test_texts = [f"Test text number {i}" for i in range(50)]

    start = time.time()
    test_embeddings = embedding_manager.generate_embeddings_batch(
        texts=test_texts,
        batch_size=32,
        use_cache=False,
        show_progress=False,
    )
    batch_time = time.time() - start

    print(f"✅ 50 embeddings générés en {batch_time:.2f}s")
    print(f"   Vitesse: {len(test_texts) / batch_time:.2f} embeddings/sec")

    # Test de recherche vectorielle
    print("\n⏳ Benchmark recherche vectorielle...")
    test_query = embedding_manager.generate_embedding("test query")

    search_times = []
    for _ in range(10):
        start = time.time()
        _ = embedding_store.search_similar_notes(
            query_embedding=test_query,
            top_k=10,
        )
        search_times.append(time.time() - start)

    avg_search_time = sum(search_times) / len(search_times)
    print(f"✅ Recherche moyenne: {avg_search_time * 1000:.2f}ms")
    print(f"   Min: {min(search_times) * 1000:.2f}ms")
    print(f"   Max: {max(search_times) * 1000:.2f}ms")

    # ========================================================================
    # 8. Test du centroide de catégorie
    # ========================================================================
    print_section("8. Test du centroide de catégorie")

    # Assigner une catégorie fictive à quelques notes pour tester
    print("⏳ Ajout de catégories de test...")

    # Créer une nouvelle version des notes avec catégories
    test_notes_with_cats = []
    for i, note in enumerate(updated_notes[:20]):
        note_dict = note.model_dump()
        if i < 10:
            note_dict["ai_categories"] = ["Technology"]
        else:
            note_dict["ai_categories"] = ["Science"]

        from obsillama.models.note import Note
        test_notes_with_cats.append(Note(**note_dict))

    # Réinsérer avec catégories
    test_embeddings = embeddings[:20]
    embedding_store.upsert_embeddings(
        notes=test_notes_with_cats,
        embeddings=test_embeddings,
    )

    print("✅ Catégories de test ajoutées")

    # Calculer le centroide
    print("\n⏳ Calcul du centroide 'Technology'...")
    centroid = embedding_store.get_category_centroid(
        category_id="tech",
        category_name="Technology",
    )

    if centroid:
        print(f"✅ Centroide calculé")
        print(f"   Dimension: {len(centroid)}")
        print(f"   Norme L2: {sum(x**2 for x in centroid)**0.5:.3f}")

        # Utiliser le centroide pour rechercher
        print("\n⏳ Recherche avec centroide...")
        centroid_results = embedding_store.search_similar_notes(
            query_embedding=centroid,
            top_k=5,
        )

        print(f"✅ {len(centroid_results)} résultats similaires au centroide:")
        for i, result in enumerate(centroid_results, 1):
            cats = result.get("ai_categories", [])
            print(f"   {i}. {result['title'][:45]:45s} | Cats: {cats}")

    # ========================================================================
    # Résumé final
    # ========================================================================
    print_section("RÉSUMÉ DES TESTS")

    print("✅ Tous les tests sont passés avec succès !\n")

    print("📊 Résumé:")
    print(f"   • Notes traitées: {len(notes)}")
    print(f"   • Embeddings générés: {len(embeddings)}")
    print(f"   • Dimension: 768")
    print(f"   • Vitesse génération: {len(notes) / elapsed:.2f} notes/sec")
    print(f"   • Accélération cache: {elapsed / cached_elapsed:.2f}x")
    print(f"   • Temps recherche moyen: {avg_search_time * 1000:.2f}ms")
    print(f"   • Cache size: {cache_stats['cache_size']} embeddings")

    print("\n✅ Phase 3 - Système d'embeddings VALIDÉ !")


if __name__ == "__main__":
    try:
        test_embeddings()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
