"""
Test rapide pour valider les embeddings et la sauvegarde GraphRAG.

Ce test utilise des entités/relations/communautés créées manuellement
pour tester uniquement la génération d'embeddings et la sauvegarde.
"""

import logging
from obsillama.llm.ollama_client import OllamaClient
from obsillama.storage.graph_store import GraphStore
from obsillama.models.graph_entity import (
    GraphEntity,
    GraphRelationship,
    GraphCommunity,
    EntityType,
    RelationshipType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_embeddings_and_storage():
    """Test des embeddings et de la sauvegarde."""

    logger.info("=" * 80)
    logger.info("TEST EMBEDDINGS + SAUVEGARDE GRAPHRAG")
    logger.info("=" * 80)

    # Créer des entités de test
    entities = [
        GraphEntity(
            id="ent_1",
            name="Python",
            type=EntityType.TECHNOLOGY,
            description="Langage de programmation de haut niveau",
            importance_score=0.9,
        ),
        GraphEntity(
            id="ent_2",
            name="Docker",
            type=EntityType.TECHNOLOGY,
            description="Plateforme de conteneurisation",
            importance_score=0.85,
        ),
        GraphEntity(
            id="ent_3",
            name="Machine Learning",
            type=EntityType.CONCEPT,
            description="Domaine de l'intelligence artificielle",
            importance_score=0.95,
        ),
    ]

    # Créer des relations de test
    relationships = [
        GraphRelationship(
            id="rel_1",
            source_entity_id="ent_1",
            target_entity_id="ent_2",
            relationship_type=RelationshipType.USES,
            description="Python peut utiliser Docker",
            confidence=0.9,
        ),
    ]

    # Créer des communautés de test (vide pour ce test)
    communities = []

    logger.info(f"\nDonnées de test créées:")
    logger.info(f"  - {len(entities)} entités")
    logger.info(f"  - {len(relationships)} relations")
    logger.info(f"  - {len(communities)} communautés")

    # Initialiser Ollama et GraphStore
    client = OllamaClient()
    store = GraphStore()

    # Nettoyer les anciennes données
    logger.info("\nNettoyage des anciennes données...")
    try:
        store.clear_graph()
        logger.info("  → Anciennes données supprimées")
    except Exception as e:
        logger.info(f"  → Aucune donnée à supprimer ({e})")

    # Générer embeddings
    logger.info("\nGénération des embeddings...")
    entity_texts = [
        f"{e.name}: {e.description}" if e.description else e.name
        for e in entities
    ]
    entity_embeddings = client.embed_batch(entity_texts, show_progress=True)
    logger.info(f"  → {len(entity_embeddings)} embeddings générés")

    # Vérifier dimensions
    for i, emb in enumerate(entity_embeddings):
        logger.info(f"  Entity {i+1}: dimension={len(emb)}")
        assert len(emb) == 768, f"Embedding devrait être de dimension 768, obtenu {len(emb)}"

    # Sauvegarder
    logger.info("\nSauvegarde dans GraphStore...")
    store.save_graph(
        entities=entities,
        relationships=relationships,
        communities=communities,
        entity_embeddings=entity_embeddings,
        community_embeddings=[],  # Pas de communautés
    )
    logger.info("  → Sauvegarde réussie")

    # Charger
    logger.info("\nChargement depuis GraphStore...")
    loaded_entities, loaded_relationships, loaded_communities = store.load_graph()

    logger.info(f"  → {len(loaded_entities)} entités chargées")
    logger.info(f"  → {len(loaded_relationships)} relations chargées")
    logger.info(f"  → {len(loaded_communities)} communautés chargées")

    # Validations
    assert len(loaded_entities) == len(entities), "Nombre d'entités incorrect"
    assert len(loaded_relationships) == len(relationships), "Nombre de relations incorrect"

    # Vérifier une entité
    loaded_python = next((e for e in loaded_entities if e.name == "Python"), None)
    assert loaded_python is not None, "Entité Python non trouvée"
    assert loaded_python.type == EntityType.TECHNOLOGY
    assert loaded_python.importance_score == 0.9

    logger.info("\n✅ TEST RÉUSSI !")
    logger.info("  - Embeddings générés correctement (dimension 768)")
    logger.info("  - Sauvegarde dans LanceDB + JSON réussie")
    logger.info("  - Chargement validé")

    return True

if __name__ == "__main__":
    try:
        test_embeddings_and_storage()
    except Exception as e:
        logger.error(f"\n❌ TEST ÉCHOUÉ: {e}", exc_info=True)
        raise
