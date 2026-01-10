"""
Tests pour le Category Generator.

Ce test valide le générateur de catégories avec des données synthétiques.
"""

import logging
from obsillama.llm.ollama_client import OllamaClient
from obsillama.core.category_generator import CategoryGenerator
from obsillama.storage.category_store import CategoryStore
from obsillama.models.note import Note
from obsillama.models.graph_entity import (
    GraphEntity,
    GraphCommunity,
    EntityType,
)
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_category_generator():
    """
    Test complet du générateur de catégories.

    Ce test :
    1. Crée des communautés synthétiques
    2. Génère des catégories via CategoryGenerator
    3. Génère des embeddings pour notes et catégories
    4. Assigne les notes aux catégories
    5. Sauvegarde dans CategoryStore
    """
    logger.info("=" * 80)
    logger.info("TEST CATEGORY GENERATOR")
    logger.info("=" * 80)

    # Initialiser clients
    client = OllamaClient()
    generator = CategoryGenerator(
        ollama_client=client,
        target_category_count=5,
        min_notes_per_category=2,
        confidence_threshold=0.6,
    )
    store = CategoryStore()

    # Nettoyer les anciennes données
    logger.info("\nNettoyage des anciennes données...")
    try:
        store.clear()
        logger.info("  → Anciennes données supprimées")
    except Exception as e:
        logger.info(f"  → Aucune donnée à supprimer ({e})")

    # Phase 1 : Créer des communautés synthétiques
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1 : Création de communautés synthétiques")
    logger.info("=" * 80)

    # Communauté 1 : Technologies Python
    python_entities = [
        GraphEntity(
            id="e1",
            name="Python",
            type=EntityType.TECHNOLOGY,
            description="Langage de programmation",
            importance_score=0.95,
        ),
        GraphEntity(
            id="e2",
            name="Django",
            type=EntityType.TECHNOLOGY,
            description="Framework web Python",
            importance_score=0.9,
        ),
        GraphEntity(
            id="e3",
            name="Flask",
            type=EntityType.TECHNOLOGY,
            description="Micro-framework web Python",
            importance_score=0.85,
        ),
        GraphEntity(
            id="e4",
            name="FastAPI",
            type=EntityType.TECHNOLOGY,
            description="Framework API moderne Python",
            importance_score=0.88,
        ),
    ]

    community_python = GraphCommunity(
        id="comm_python",
        name="",
        description="Communauté regroupant les technologies Python pour le développement web",
        entity_ids=[e.id for e in python_entities],
        entity_count=len(python_entities),
        keywords=["Python", "Web", "Framework"],
        density=0.75,
    )

    # Communauté 2 : DevOps / Infrastructure
    devops_entities = [
        GraphEntity(
            id="e5",
            name="Docker",
            type=EntityType.TECHNOLOGY,
            description="Plateforme de conteneurisation",
            importance_score=0.92,
        ),
        GraphEntity(
            id="e6",
            name="Kubernetes",
            type=EntityType.TECHNOLOGY,
            description="Orchestrateur de conteneurs",
            importance_score=0.9,
        ),
        GraphEntity(
            id="e7",
            name="Terraform",
            type=EntityType.TECHNOLOGY,
            description="Outil d'infrastructure as code",
            importance_score=0.87,
        ),
    ]

    community_devops = GraphCommunity(
        id="comm_devops",
        name="",
        description="Communauté regroupant les outils DevOps et d'infrastructure cloud",
        entity_ids=[e.id for e in devops_entities],
        entity_count=len(devops_entities),
        keywords=["DevOps", "Container", "Infrastructure"],
        density=0.8,
    )

    all_entities = python_entities + devops_entities
    communities = [community_python, community_devops]

    logger.info(f"Communautés créées : {len(communities)}")
    for comm in communities:
        logger.info(f"  - {comm.id} : {comm.entity_count} entités")

    # Phase 2 : Générer des catégories
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2 : Génération des catégories")
    logger.info("=" * 80)

    categories = generator.generate_from_communities(communities, all_entities)

    logger.info(f"\nCatégories générées : {len(categories)}")
    for cat in categories:
        logger.info(f"  - {cat.name}")
        logger.info(f"    Description : {cat.description[:100]}...")
        logger.info(f"    Keywords : {', '.join(cat.keywords[:5])}")
        logger.info(f"    Tag : {cat.tag_name}")

    assert len(categories) > 0, "Aucune catégorie générée"

    # Phase 3 : Créer des notes de test
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3 : Création de notes de test")
    logger.info("=" * 80)

    notes = [
        Note(
            id="n1",
            file_path="/vault/python_django.md",
            file_name="python_django.md",
            relative_path="python_django.md",
            title="Tutoriel Django",
            content="Django est un framework web Python très populaire. Il permet de créer rapidement des applications web robustes.",
        ),
        Note(
            id="n2",
            file_path="/vault/python_flask.md",
            file_name="python_flask.md",
            relative_path="python_flask.md",
            title="Getting Started with Flask",
            content="Flask est un micro-framework Python idéal pour les petites applications et les APIs.",
        ),
        Note(
            id="n3",
            file_path="/vault/docker_basics.md",
            file_name="docker_basics.md",
            relative_path="docker_basics.md",
            title="Introduction à Docker",
            content="Docker permet de conteneuriser vos applications pour un déploiement facile. Kubernetes peut orchestrer ces conteneurs.",
        ),
        Note(
            id="n4",
            file_path="/vault/devops_k8s.md",
            file_name="devops_k8s.md",
            relative_path="devops_k8s.md",
            title="Kubernetes en production",
            content="Kubernetes est l'orchestrateur de conteneurs de référence. Il fonctionne très bien avec Docker et Terraform.",
        ),
        Note(
            id="n5",
            file_path="/vault/python_fastapi.md",
            file_name="python_fastapi.md",
            relative_path="python_fastapi.md",
            title="FastAPI Tutorial",
            content="FastAPI est un framework Python moderne pour créer des APIs. Il est très rapide et utilise les types Python.",
        ),
    ]

    logger.info(f"Notes créées : {len(notes)}")

    # Phase 4 : Générer embeddings
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4 : Génération des embeddings")
    logger.info("=" * 80)

    # Embeddings des notes
    note_texts = [f"{n.title}: {n.content}" for n in notes]
    logger.info(f"Génération embeddings pour {len(note_texts)} notes...")
    note_embeddings = client.embed_batch(note_texts, show_progress=True)
    logger.info(f"  → {len(note_embeddings)} embeddings générés")

    # Embeddings des catégories
    category_texts = [
        f"{c.name}: {c.description}" if c.description else c.name
        for c in categories
    ]
    logger.info(f"Génération embeddings pour {len(category_texts)} catégories...")
    category_embeddings = client.embed_batch(category_texts, show_progress=True)
    logger.info(f"  → {len(category_embeddings)} embeddings générés")

    # Phase 5 : Assigner notes aux catégories
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 5 : Assignation des notes aux catégories")
    logger.info("=" * 80)

    assignments = generator.assign_notes_to_categories(
        notes=notes,
        categories=categories,
        note_embeddings=note_embeddings,
        category_embeddings=category_embeddings,
    )

    logger.info(f"\nAssignations créées :")
    for cat in categories:
        if cat.id in assignments:
            notes_list = assignments[cat.id]
            logger.info(f"  - {cat.name} : {len(notes_list)} notes")
            for note_id, confidence in notes_list:
                note = next((n for n in notes if n.id == note_id), None)
                if note:
                    logger.info(
                        f"      • {note.title} (confidence={confidence:.2f})"
                    )

    assert len(assignments) > 0, "Aucune assignation créée"

    # Phase 6 : Sauvegarder
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 6 : Sauvegarde dans CategoryStore")
    logger.info("=" * 80)

    logger.info("Sauvegarde de la taxonomie...")
    store.save_taxonomy(categories)

    logger.info("Sauvegarde des assignations...")
    store.save_assignments(assignments)

    logger.info("  → Sauvegarde terminée")

    # Phase 7 : Charger et vérifier
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 7 : Chargement et vérification")
    logger.info("=" * 80)

    loaded_categories = store.load_taxonomy()
    loaded_assignments = store.load_assignments()

    logger.info(f"Catégories chargées : {len(loaded_categories)}")
    logger.info(f"Assignations chargées : {len(loaded_assignments)}")

    assert len(loaded_categories) == len(
        categories
    ), "Nombre de catégories différent"
    assert len(loaded_assignments) == len(
        assignments
    ), "Nombre d'assignations différent"

    # Phase 8 : Statistiques
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 8 : Statistiques")
    logger.info("=" * 80)

    stats = store.get_stats()
    logger.info(f"Statistiques :")
    logger.info(f"  - Total catégories : {stats['total_categories']}")
    logger.info(f"  - Catégories approuvées : {stats['approved_categories']}")
    logger.info(f"  - Catégories en attente : {stats['pending_categories']}")
    logger.info(f"  - Total assignations : {stats['total_assignments']}")
    logger.info(
        f"  - Moyenne notes/catégorie : {stats['avg_notes_per_category']:.1f}"
    )

    # Résumé final
    logger.info("\n" + "=" * 80)
    logger.info("RÉSUMÉ DU TEST")
    logger.info("=" * 80)
    logger.info(f"✅ Communautés synthétiques : {len(communities)}")
    logger.info(f"✅ Catégories générées : {len(categories)}")
    logger.info(f"✅ Notes de test : {len(notes)}")
    logger.info(f"✅ Embeddings générés : {len(note_embeddings) + len(category_embeddings)}")
    logger.info(f"✅ Assignations créées : {sum(len(v) for v in assignments.values())}")
    logger.info(f"✅ Sauvegarde/Chargement validés")
    logger.info("\n🎉 TEST CATEGORY GENERATOR : SUCCÈS !\n")

    return categories, assignments


if __name__ == "__main__":
    """
    Exécution directe du test (hors pytest).
    """
    print("\n" + "=" * 80)
    print("EXÉCUTION DIRECTE DU TEST CATEGORY GENERATOR")
    print("=" * 80 + "\n")

    try:
        test_category_generator()
    except Exception as e:
        logger.error(f"\n❌ TEST ÉCHOUÉ : {e}", exc_info=True)
        raise
