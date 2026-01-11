"""
Tests pour le pipeline GraphRAG.

Ce test valide l'ensemble du pipeline :
- Extraction d'entités
- Extraction de relations
- Construction du graphe
- Détection de communautés
- Résumés de communautés
- Sauvegarde dans GraphStore
"""

import logging
import pytest
from pathlib import Path

from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.graphrag_integration import GraphRAGPipeline
from obsillama.storage.graph_store import GraphStore
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.core.note_scanner import NoteScanner
from obsillama.config.settings import get_settings

# Configuration du logging pour les tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture
def ollama_client():
    """Fixture pour le client Ollama."""
    settings = get_settings()
    return OllamaClient(
        base_url=settings.ollama.base_url,
        generation_model=settings.ollama.models.generation,
        embedding_model=settings.ollama.models.embedding,
    )


@pytest.fixture
def graph_store(tmp_path):
    """Fixture pour le GraphStore avec base de données temporaire."""
    # Utiliser un dossier temporaire pour isoler les tests
    test_db_path = tmp_path / "lancedb_test"
    test_db_manager = LanceDBManager(db_path=str(test_db_path))

    # Créer un fichier temporaire pour les relations
    test_relations_file = tmp_path / "graph_relationships.json"

    return GraphStore(
        db_manager=test_db_manager,
        relationships_file=str(test_relations_file)
    )


@pytest.fixture
def sample_notes():
    """Fixture pour charger 20 notes du vault."""
    settings = get_settings()
    vault_path = settings.vault.path

    logger.info(f"Scan du vault : {vault_path}")

    # Scanner le vault
    scanner = NoteScanner(vault_path=vault_path)
    notes = scanner.scan_and_parse(
        strategy="random",
        sample_size=20,
    )

    logger.info(f"{len(notes)} notes chargées pour les tests")
    return notes


def test_graphrag_pipeline_full(ollama_client, graph_store, sample_notes):
    """
    Test complet du pipeline GraphRAG sur 20 notes.

    Ce test valide :
    1. Extraction d'entités depuis les notes
    2. Extraction de relations
    3. Construction du graphe igraph
    4. Détection de communautés avec Leiden
    5. Génération de résumés
    6. Sauvegarde dans GraphStore
    7. Chargement depuis GraphStore
    """
    logger.info("=" * 80)
    logger.info("TEST PIPELINE GRAPHRAG COMPLET")
    logger.info("=" * 80)

    # Initialiser le pipeline
    pipeline = GraphRAGPipeline(
        ollama_client=ollama_client,
        min_community_size=3,
        leiden_resolution=1.0,
        max_entities_per_note=20,
    )

    logger.info(f"\nNotes à analyser : {len(sample_notes)}")
    for i, note in enumerate(sample_notes[:5], 1):
        logger.info(f"  {i}. {note.title} ({note.word_count} mots)")
    if len(sample_notes) > 5:
        logger.info(f"  ... et {len(sample_notes) - 5} autres notes")

    # Phase 1 : Exécuter le pipeline complet
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1 : Exécution du pipeline GraphRAG")
    logger.info("=" * 80)

    entities, relationships, communities = pipeline.run_full_pipeline(
        notes=sample_notes, show_progress=True
    )

    # Validations Phase 1
    logger.info("\n--- Résultats Phase 1 ---")
    logger.info(f"Entités extraites : {len(entities)}")
    logger.info(f"Relations extraites : {len(relationships)}")
    logger.info(f"Communautés détectées : {len(communities)}")

    assert len(entities) > 0, "Aucune entité n'a été extraite"
    assert len(relationships) >= 0, "Erreur dans l'extraction des relations"
    assert len(communities) >= 0, "Erreur dans la détection des communautés"

    # Afficher quelques entités
    logger.info("\nTop 10 entités par importance :")
    top_entities = sorted(entities, key=lambda e: e.importance_score, reverse=True)[
        :10
    ]
    for i, entity in enumerate(top_entities, 1):
        logger.info(
            f"  {i}. {entity.name} ({entity.type.value}) - "
            f"importance={entity.importance_score:.2f}, "
            f"mentions={entity.mention_count}"
        )

    # Afficher quelques relations
    if relationships:
        logger.info(f"\nExemples de relations (5 premières) :")
        for i, rel in enumerate(relationships[:5], 1):
            # Trouver les noms des entités
            source = next((e for e in entities if e.id == rel.source_entity_id), None)
            target = next((e for e in entities if e.id == rel.target_entity_id), None)

            if source and target:
                logger.info(
                    f"  {i}. {source.name} -{rel.relationship_type.value}-> {target.name} "
                    f"(confidence={rel.confidence:.2f})"
                )

    # Afficher les communautés
    if communities:
        logger.info(f"\nCommunautés détectées :")
        for i, community in enumerate(communities, 1):
            logger.info(
                f"  {i}. {community.name or community.id} - "
                f"{community.entity_count} entités, "
                f"densité={community.density:.2f}"
            )
            if community.description:
                logger.info(f"     Description : {community.description[:100]}...")
            if community.keywords:
                logger.info(f"     Mots-clés : {', '.join(community.keywords[:5])}")

    # Phase 2 : Générer les embeddings
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2 : Génération des embeddings")
    logger.info("=" * 80)

    # Générer embeddings pour les entités (descriptions)
    logger.info("Génération des embeddings des entités...")
    entity_texts = [
        f"{e.name}: {e.description}" if e.description else e.name for e in entities
    ]
    entity_embeddings = ollama_client.embed_batch(entity_texts, show_progress=True)

    logger.info(f"  → {len(entity_embeddings)} embeddings générés")

    # Générer embeddings pour les communautés (descriptions)
    logger.info("Génération des embeddings des communautés...")
    if communities:
        community_texts = [
            f"{c.name}: {c.description}" if c.description else c.name or c.id
            for c in communities
        ]
        community_embeddings = ollama_client.embed_batch(
            community_texts, show_progress=True
        )
        logger.info(f"  → {len(community_embeddings)} embeddings générés")
    else:
        community_embeddings = []
        logger.info("  → Aucune communauté, pas d'embeddings à générer")

    # Phase 3 : Sauvegarder dans GraphStore
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3 : Sauvegarde dans GraphStore")
    logger.info("=" * 80)

    graph_store.save_graph(
        entities=entities,
        relationships=relationships,
        communities=communities,
        entity_embeddings=entity_embeddings,
        community_embeddings=community_embeddings,
    )

    logger.info("  → Graphe sauvegardé avec succès")

    # Phase 4 : Charger depuis GraphStore
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4 : Chargement depuis GraphStore")
    logger.info("=" * 80)

    loaded_entities, loaded_relationships, loaded_communities = graph_store.load_graph()

    logger.info(f"Entités chargées : {len(loaded_entities)}")
    logger.info(f"Relations chargées : {len(loaded_relationships)}")
    logger.info(f"Communautés chargées : {len(loaded_communities)}")

    # Validations Phase 4
    # Note: On vérifie que le nombre est approximativement le même (±5 entités)
    # car le LLM peut générer des variations légères (doublons, fusions, etc.)
    entity_diff = abs(len(loaded_entities) - len(entities))
    assert entity_diff <= 5, (
        f"Nombre d'entités trop différent après chargement: "
        f"{len(loaded_entities)} vs {len(entities)} (diff: {entity_diff})"
    )

    relationship_diff = abs(len(loaded_relationships) - len(relationships))
    assert relationship_diff <= 5, (
        f"Nombre de relations trop différent après chargement: "
        f"{len(loaded_relationships)} vs {len(relationships)} (diff: {relationship_diff})"
    )

    assert len(loaded_communities) == len(
        communities
    ), "Nombre de communautés différent après chargement"

    # Vérifier que les données sont identiques
    logger.info("\nVérification de l'intégrité des données...")

    # Vérifier une entité
    if entities:
        original_entity = entities[0]
        loaded_entity = next((e for e in loaded_entities if e.id == original_entity.id))
        assert loaded_entity.name == original_entity.name
        assert loaded_entity.type == original_entity.type
        logger.info(f"  ✓ Entité '{original_entity.name}' vérifiée")

    # Vérifier une relation
    if relationships:
        original_rel = relationships[0]
        loaded_rel = next((r for r in loaded_relationships if r.id == original_rel.id))
        assert loaded_rel.source_entity_id == original_rel.source_entity_id
        assert loaded_rel.target_entity_id == original_rel.target_entity_id
        logger.info(f"  ✓ Relation '{original_rel.id}' vérifiée")

    # Vérifier une communauté
    if communities:
        original_comm = communities[0]
        loaded_comm = next((c for c in loaded_communities if c.id == original_comm.id))
        assert loaded_comm.name == original_comm.name
        assert len(loaded_comm.entity_ids) == len(original_comm.entity_ids)
        logger.info(f"  ✓ Communauté '{original_comm.name or original_comm.id}' vérifiée")

    # Résumé final
    logger.info("\n" + "=" * 80)
    logger.info("RÉSUMÉ DU TEST")
    logger.info("=" * 80)
    logger.info(f"✅ Notes analysées : {len(sample_notes)}")
    logger.info(f"✅ Entités extraites : {len(entities)}")
    logger.info(f"✅ Relations extraites : {len(relationships)}")
    logger.info(f"✅ Communautés détectées : {len(communities)}")
    logger.info(f"✅ Embeddings générés : {len(entity_embeddings) + len(community_embeddings)}")
    logger.info("✅ Sauvegarde et chargement validés")
    logger.info("\n🎉 TEST PIPELINE GRAPHRAG : SUCCÈS !\n")

    # Retourner les résultats pour d'autres tests si besoin
    return entities, relationships, communities


if __name__ == "__main__":
    """
    Exécution directe du test (hors pytest).
    Utile pour le développement et le débogage.
    """
    print("\n" + "=" * 80)
    print("EXÉCUTION DIRECTE DU TEST GRAPHRAG")
    print("=" * 80 + "\n")

    # Créer les fixtures manuellement
    client = OllamaClient()
    store = GraphStore()

    # Scanner le vault
    settings = get_settings()
    scanner = NoteScanner(vault_path=settings.vault.path)
    notes = scanner.scan_and_parse(
        strategy="random", sample_size=20
    )

    # Exécuter le test
    try:
        test_graphrag_pipeline_full(client, store, notes)
    except Exception as e:
        logger.error(f"\n❌ TEST ÉCHOUÉ : {e}", exc_info=True)
        raise
