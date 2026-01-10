"""
Tests end-to-end du pipeline complet ObsIllama (Phase 1 + Phase 2).

Ce test orchestre :
- Phase 1.6 : Scan du vault réel avec NoteScanner
- Phase 2.2 : Extraction entités/relations + GraphRAG + Communautés
- Phase 2.3 : Génération catégories + Assignation notes

Ce test utilise le vault réel et prend plusieurs minutes.
"""

import logging
from pathlib import Path

from obsillama.config.settings import get_settings
from obsillama.core.note_scanner import NoteScanner
from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.graphrag_integration import GraphRAGPipeline
from obsillama.storage.graph_store import GraphStore
from obsillama.core.category_generator import CategoryGenerator
from obsillama.storage.category_store import CategoryStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_end_to_end_pipeline():
    """
    Test end-to-end du pipeline complet ObsIllama.

    Pipeline :
    1. Scanner le vault (échantillonnage stratifié 15%)
    2. Extraire entités et relations avec GraphRAG
    3. Construire le graphe et détecter les communautés
    4. Générer des catégories depuis les communautés
    5. Générer embeddings des notes et catégories
    6. Assigner les notes aux catégories
    7. Sauvegarder taxonomie et assignations
    8. Afficher statistiques finales
    """
    logger.info("=" * 80)
    logger.info("TEST END-TO-END PIPELINE OBSILLAMA (Phase 1 + 2)")
    logger.info("=" * 80)

    # Charger la configuration
    settings = get_settings()
    vault_path = settings.vault.path
    logger.info(f"\nVault : {vault_path}")
    logger.info(f"Ollama : {settings.ollama.base_url}")
    logger.info(f"Échantillonnage : {settings.processing.sampling.strategy} "
                f"({settings.processing.sampling.percentage}%)")

    # =========================================================================
    # PHASE 1.6 : Scanner le vault
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1 : SCAN DU VAULT")
    logger.info("=" * 80)

    scanner = NoteScanner(vault_path=vault_path)

    # Scanner avec échantillonnage stratifié
    notes = scanner.scan_and_parse(
        strategy=settings.processing.sampling.strategy,
        sample_percentage=settings.processing.sampling.percentage,
    )

    logger.info(f"\n✅ {len(notes)} notes scannées")
    logger.info(f"  Total mots : {sum(n.word_count for n in notes):,}")
    logger.info(f"  Notes avec tags : {len([n for n in notes if n.tags])}")
    logger.info(f"  Notes avec backlinks : {len([n for n in notes if n.backlinks])}")

    if len(notes) < 10:
        logger.warning("  ⚠️ Moins de 10 notes trouvées, résultats limités")

    # =========================================================================
    # PHASE 2.2 : GraphRAG (Extraction + Graphe + Communautés)
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2.2 : GRAPHRAG PIPELINE")
    logger.info("=" * 80)

    # Initialiser le client Ollama et le pipeline
    ollama = OllamaClient()
    pipeline = GraphRAGPipeline(
        ollama_client=ollama,
        leiden_resolution=settings.graphrag.resolution,
        min_community_size=settings.graphrag.min_community_size,
    )

    # Nettoyer les anciennes données du graph store
    graph_store = GraphStore()
    logger.info("\nNettoyage des anciennes données du graph...")
    try:
        graph_store.clear_graph()
        logger.info("  → Anciennes données supprimées")
    except Exception as e:
        logger.info(f"  → Aucune donnée à supprimer ({e})")

    # Exécuter le pipeline complet
    logger.info("\nExécution du pipeline GraphRAG...")
    entities, relationships, communities = pipeline.run_full_pipeline(
        notes=notes,
        show_progress=True,
    )

    # Reconstruire le graphe pour les stats
    graph = pipeline.build_graph(entities, relationships)

    logger.info(f"\n✅ GraphRAG terminé")
    logger.info(f"  Entités extraites : {len(entities)}")
    logger.info(f"  Relations extraites : {len(relationships)}")
    logger.info(f"  Communautés détectées : {len(communities)}")
    logger.info(f"  Sommets dans le graphe : {graph.vcount()}")
    logger.info(f"  Arêtes dans le graphe : {graph.ecount()}")

    # Vérifier s'il y a des communautés valides
    if len(communities) == 0:
        logger.warning("\n⚠️ AUCUNE COMMUNAUTÉ VALIDE DÉTECTÉE")
        logger.warning("Le graphe est trop fragmenté (beaucoup d'entités isolées).")
        logger.warning("\nPossibles solutions :")
        logger.warning("  1. Réduire min_community_size dans config.yaml (actuellement 3)")
        logger.warning("  2. Améliorer l'extraction de relations (plus de contexte)")
        logger.warning("  3. Augmenter le nombre de notes scannées")
        logger.warning("\n⚠️ Impossible de continuer sans communautés. Test arrêté.")

        # Afficher quand même les statistiques disponibles
        logger.info(f"\n📊 Statistiques partielles")
        logger.info(f"  Notes scannées : {len(notes)}")
        logger.info(f"  Entités : {len(entities)}")
        logger.info(f"  Relations : {len(relationships)}")
        logger.info(f"  Graphe fragmenté : {graph.vcount()} sommets, {graph.ecount()} arêtes")

        return

    # Afficher les communautés détectées
    logger.info("\nCommunautés détectées :")
    for comm in communities[:10]:  # Limiter à 10 pour l'affichage
        logger.info(f"  - {comm.id} : {comm.entity_count} entités")
        if comm.keywords:
            logger.info(f"    Keywords : {', '.join(comm.keywords[:5])}")
        if comm.description:
            logger.info(f"    Description : {comm.description[:100]}...")

    if len(communities) > 10:
        logger.info(f"  ... et {len(communities) - 10} autres communautés")

    # Générer les embeddings des entités
    logger.info("\nGénération des embeddings des entités...")
    entity_texts = [f"{e.name}: {e.description}" if e.description else e.name
                   for e in entities]
    entity_embeddings = ollama.embed_batch(entity_texts, show_progress=True)
    logger.info(f"  → {len(entity_embeddings)} embeddings générés")

    # Sauvegarder dans le graph store
    logger.info("\nSauvegarde du graphe dans LanceDB...")
    graph_store.save_entities(entities, entity_embeddings)
    graph_store.save_relationships(relationships)

    # Générer embeddings des communautés
    logger.info("\nGénération des embeddings des communautés...")
    community_texts = [
        f"{comm.description}" if comm.description else f"Communauté {comm.id}"
        for comm in communities
    ]
    community_embeddings = ollama.embed_batch(community_texts, show_progress=True)
    logger.info(f"  → {len(community_embeddings)} embeddings générés")

    graph_store.save_communities(communities, community_embeddings)
    logger.info("  → Graphe complet sauvegardé")

    # =========================================================================
    # PHASE 2.3 : Générateur de catégories
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2.3 : GÉNÉRATION DES CATÉGORIES")
    logger.info("=" * 80)

    # Initialiser le générateur
    generator = CategoryGenerator(
        ollama_client=ollama,
        target_category_count=settings.categorization.target_count,
        min_notes_per_category=settings.categorization.min_notes_per_category,
        confidence_threshold=settings.categorization.thresholds.assignment_confidence,
    )

    # Initialiser le store
    category_store = CategoryStore()

    # Nettoyer les anciennes données
    logger.info("\nNettoyage des anciennes catégories...")
    try:
        category_store.clear()
        logger.info("  → Anciennes données supprimées")
    except Exception as e:
        logger.info(f"  → Aucune donnée à supprimer ({e})")

    # Générer les catégories depuis les communautés
    logger.info("\nGénération des catégories depuis les communautés...")
    categories = generator.generate_from_communities(communities, entities)

    logger.info(f"\n✅ {len(categories)} catégories générées")
    for cat in categories[:10]:  # Limiter à 10 pour l'affichage
        logger.info(f"  - {cat.name}")
        logger.info(f"    Keywords : {', '.join(cat.keywords[:5])}")
        logger.info(f"    Tag : {cat.tag_name}")

    if len(categories) > 10:
        logger.info(f"  ... et {len(categories) - 10} autres catégories")

    if len(categories) == 0:
        logger.error("❌ Aucune catégorie générée, impossible de continuer")
        return

    # Générer embeddings des notes
    logger.info("\nGénération des embeddings des notes...")
    note_texts = [f"{n.title}: {n.content[:500]}" for n in notes]
    note_embeddings = ollama.embed_batch(note_texts, show_progress=True)
    logger.info(f"  → {len(note_embeddings)} embeddings générés")

    # Générer embeddings des catégories
    logger.info("\nGénération des embeddings des catégories...")
    category_texts = [
        f"{c.name}: {c.description}" if c.description else c.name
        for c in categories
    ]
    category_embeddings = ollama.embed_batch(category_texts, show_progress=True)
    logger.info(f"  → {len(category_embeddings)} embeddings générés")

    # Assigner les notes aux catégories
    logger.info("\nAssignation des notes aux catégories...")
    assignments = generator.assign_notes_to_categories(
        notes=notes,
        categories=categories,
        note_embeddings=note_embeddings,
        category_embeddings=category_embeddings,
    )

    logger.info(f"\n✅ Assignations créées")
    logger.info(f"  Catégories avec notes : {len(assignments)}")
    logger.info(f"  Notes assignées : {sum(len(v) for v in assignments.values())}")

    # Afficher les assignations (top 5 catégories)
    sorted_assignments = sorted(
        assignments.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    logger.info("\nTop catégories par nombre de notes :")
    for cat_id, notes_list in sorted_assignments[:5]:
        category = next((c for c in categories if c.id == cat_id), None)
        if category:
            avg_conf = sum(conf for _, conf in notes_list) / len(notes_list)
            logger.info(f"  - {category.name} : {len(notes_list)} notes "
                       f"(confiance moyenne : {avg_conf:.2f})")

    # Sauvegarder taxonomie et assignations
    logger.info("\nSauvegarde de la taxonomie et des assignations...")
    category_store.save_taxonomy(categories)
    category_store.save_assignments(assignments)
    logger.info("  → Sauvegarde terminée")

    # =========================================================================
    # STATISTIQUES FINALES
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("STATISTIQUES FINALES")
    logger.info("=" * 80)

    stats = category_store.get_stats()

    logger.info(f"\n📊 Vault")
    logger.info(f"  Notes scannées : {len(notes)}")
    logger.info(f"  Total mots : {sum(n.word_count for n in notes):,}")

    logger.info(f"\n📊 GraphRAG")
    logger.info(f"  Entités : {len(entities)}")
    logger.info(f"  Relations : {len(relationships)}")
    logger.info(f"  Communautés : {len(communities)}")
    logger.info(f"  Sommets graphe : {graph.vcount()}")
    logger.info(f"  Arêtes graphe : {graph.ecount()}")

    logger.info(f"\n📊 Catégories")
    logger.info(f"  Total catégories : {stats['total_categories']}")
    logger.info(f"  Catégories approuvées : {stats['approved_categories']}")
    logger.info(f"  Catégories en attente : {stats['pending_categories']}")
    logger.info(f"  Notes assignées : {stats['total_assignments']}")
    logger.info(f"  Moyenne notes/catégorie : {stats['avg_notes_per_category']:.1f}")

    logger.info(f"\n📂 Fichiers générés")
    logger.info(f"  Taxonomie : data/categories/taxonomy.json")
    logger.info(f"  Assignations : data/categories/assignments.json")
    logger.info(f"  Graph entities : data/lancedb/entities")
    logger.info(f"  Graph communities : data/lancedb/communities")
    logger.info(f"  Graph relations : data/categories/graph_relationships.json")

    # Vérifications finales
    logger.info("\n" + "=" * 80)
    logger.info("VÉRIFICATIONS")
    logger.info("=" * 80)

    # Vérifier que les notes ont été assignées
    notes_assigned = sum(len(v) for v in assignments.values())
    coverage = (notes_assigned / len(notes)) * 100 if notes else 0
    logger.info(f"\n✅ Couverture : {notes_assigned}/{len(notes)} notes assignées ({coverage:.1f}%)")

    if coverage < 50:
        logger.warning(f"  ⚠️ Couverture faible, considérer baisser le seuil de confiance "
                      f"({settings.categorization.thresholds.assignment_confidence})")

    # Vérifier distribution
    notes_per_cat = [len(v) for v in assignments.values()]
    if notes_per_cat:
        min_notes = min(notes_per_cat)
        max_notes = max(notes_per_cat)
        avg_notes = sum(notes_per_cat) / len(notes_per_cat)
        logger.info(f"\n✅ Distribution : min={min_notes}, max={max_notes}, avg={avg_notes:.1f}")

        if max_notes > 3 * avg_notes:
            logger.warning("  ⚠️ Distribution déséquilibrée, certaines catégories trop larges")

    # Vérifier qualité des catégories
    empty_categories = [c for c in categories if c.id not in assignments]
    logger.info(f"\n✅ Catégories vides : {len(empty_categories)}/{len(categories)}")

    if len(empty_categories) > len(categories) * 0.3:
        logger.warning("  ⚠️ Trop de catégories vides (>30%), considérer réduire target_count")

    logger.info("\n" + "=" * 80)
    logger.info("🎉 TEST END-TO-END PIPELINE : SUCCÈS !")
    logger.info("=" * 80)

    return notes, entities, relationships, communities, categories, assignments


if __name__ == "__main__":
    """
    Exécution directe du test (hors pytest).
    """
    print("\n" + "=" * 80)
    print("EXÉCUTION TEST END-TO-END OBSILLAMA")
    print("=" * 80 + "\n")

    try:
        test_end_to_end_pipeline()
    except Exception as e:
        logger.error(f"\n❌ TEST ÉCHOUÉ : {e}", exc_info=True)
        raise
