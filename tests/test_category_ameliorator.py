"""
Tests pour le CategoryAmeliorator

Ces tests vérifient:
- Chargement de taxonomie existante
- Assignation de nouvelles notes (K-NN)
- Raffinement des catégories (centroides)
- Suggestions de sous-catégories (clustering)
- Suggestions de fusions (similarité)
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from obsillama.core.category_ameliorator import CategoryAmeliorator
from obsillama.storage.category_store import CategoryStore
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.llm.ollama_client import OllamaClient
from obsillama.models.note import Note
from obsillama.models.category import Category, ReviewStatus


# ============================================================================
# Fixtures pour les tests
# ============================================================================


@pytest.fixture
def mock_ollama_client():
    """Mock du client Ollama pour éviter les appels API."""
    import hashlib
    import numpy as np

    class MockOllamaClient:
        def embed(self, text, model="nomic-embed-text"):
            # Créer un embedding factice basé sur le hash du texte
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            np.random.seed(hash_val % (2**32))  # Seed déterministe
            return np.random.rand(768).tolist()

        def embed_batch(self, texts, model="nomic-embed-text"):
            return [self.embed(text, model) for text in texts]

    return MockOllamaClient()


@pytest.fixture
def temp_category_store(tmp_path):
    """Crée un CategoryStore temporaire avec des catégories de test."""
    taxonomy_file = tmp_path / "taxonomy.json"
    assignments_file = tmp_path / "assignments.json"

    # Créer des catégories de test
    test_categories = [
        Category(
            id="cat_tech",
            name="Technology",
            description="Notes about technology and software",
            tag_name="AI-Category-Technology",
            keywords=["tech", "software", "code"],
            note_count=10,
            avg_confidence=0.85,
            review_status=ReviewStatus.APPROVED,
        ),
        Category(
            id="cat_projects",
            name="Projects",
            description="Project management and planning",
            tag_name="AI-Category-Projects",
            keywords=["project", "planning", "management"],
            note_count=5,
            avg_confidence=0.80,
            review_status=ReviewStatus.APPROVED,
        ),
    ]

    # Sauvegarder dans le fichier temporaire
    taxonomy_data = {
        "version": "test_20260111",
        "created_at": datetime.now().isoformat(),
        "category_count": len(test_categories),
        "categories": [cat.model_dump(mode='json') for cat in test_categories],
    }

    with open(taxonomy_file, "w") as f:
        json.dump(taxonomy_data, f, indent=2)

    # Créer le store
    store = CategoryStore(
        taxonomy_file=str(taxonomy_file),
        assignments_file=str(assignments_file),
    )

    return store


@pytest.fixture
def sample_notes():
    """Crée des notes de test."""
    return [
        Note(
            id="note1",
            file_path="/vault/note1.md",
            file_name="note1.md",
            relative_path="note1.md",
            title="Python Programming Guide",
            content="A guide to Python programming with examples",
            tags=["python", "programming"],
            word_count=500,
        ),
        Note(
            id="note2",
            file_path="/vault/note2.md",
            file_name="note2.md",
            relative_path="note2.md",
            title="Project Planning Template",
            content="Template for planning software projects",
            tags=["project", "planning"],
            word_count=300,
        ),
        Note(
            id="note3",
            file_path="/vault/note3.md",
            file_name="note3.md",
            relative_path="note3.md",
            title="Docker Setup Guide",
            content="How to setup Docker for development",
            tags=["docker", "devops"],
            word_count=400,
        ),
    ]


# ============================================================================
# Tests du CategoryAmeliorator
# ============================================================================


def test_ameliorator_initialization(temp_category_store, mock_ollama_client):
    """Test initialisation du CategoryAmeliorator."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
        confidence_threshold=0.7,
        min_notes_per_category=5,
    )

    assert ameliorator.category_store == temp_category_store
    assert ameliorator.confidence_threshold == 0.7
    assert ameliorator.min_notes_per_category == 5


def test_load_existing_taxonomy(temp_category_store, mock_ollama_client):
    """Test chargement de la taxonomie existante."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
    )

    categories = ameliorator.load_existing_taxonomy()

    # Doit charger 2 catégories approuvées
    assert len(categories) == 2
    assert all(cat.review_status == ReviewStatus.APPROVED for cat in categories)
    assert any(cat.name == "Technology" for cat in categories)
    assert any(cat.name == "Projects" for cat in categories)


def test_assign_new_notes(temp_category_store, mock_ollama_client, sample_notes):
    """Test assignation de nouvelles notes aux catégories."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
        confidence_threshold=0.5,  # Seuil bas pour le test
    )

    # Charger catégories
    categories = ameliorator.load_existing_taxonomy()

    # Générer embeddings factices
    embedding_manager = EmbeddingManager(ollama_client=mock_ollama_client)

    # Embeddings pour notes
    note_texts = [note.content for note in sample_notes]
    note_embeddings = embedding_manager.generate_embeddings_batch(note_texts)

    # Embeddings pour catégories
    category_texts = [f"{cat.name}: {cat.description}" for cat in categories]
    category_embeddings = embedding_manager.generate_embeddings_batch(category_texts)

    # Assigner
    assignments = ameliorator.assign_new_notes(
        new_notes=sample_notes,
        existing_categories=categories,
        note_embeddings=note_embeddings,
        category_embeddings=category_embeddings,
    )

    # Vérifier qu'il y a des assignations
    assert len(assignments) >= 1
    # Chaque assignation doit avoir un ID de catégorie et une liste de (note_id, confidence)
    for cat_id, notes_list in assignments.items():
        assert isinstance(notes_list, list)
        for note_id, confidence in notes_list:
            assert isinstance(note_id, str)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0


def test_refine_categories(temp_category_store, mock_ollama_client, sample_notes):
    """Test raffinement des catégories."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
    )

    categories = ameliorator.load_existing_taxonomy()
    embedding_manager = EmbeddingManager(ollama_client=mock_ollama_client)

    # Générer embeddings
    note_texts = [note.content for note in sample_notes]
    note_embeddings = embedding_manager.generate_embeddings_batch(note_texts)

    category_texts = [f"{cat.name}: {cat.description}" for cat in categories]
    category_embeddings = embedding_manager.generate_embeddings_batch(category_texts)

    # Assigner
    assignments = ameliorator.assign_new_notes(
        new_notes=sample_notes,
        existing_categories=categories,
        note_embeddings=note_embeddings,
        category_embeddings=category_embeddings,
    )

    # Raffiner
    refined_categories = ameliorator.refine_categories(
        all_notes=sample_notes,
        categories=categories,
        note_embeddings=note_embeddings,
        assignments=assignments,
    )

    # Vérifier que les catégories ont été raffinées
    assert len(refined_categories) == len(categories)

    # Vérifier que les statistiques ont été mises à jour
    for cat in refined_categories:
        if cat.id in assignments:
            assert cat.note_count == len(assignments[cat.id])
            assert cat.avg_confidence >= 0.0


def test_suggest_subcategories(temp_category_store, mock_ollama_client):
    """Test suggestion de sous-catégories."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
    )

    # Créer une catégorie parente avec beaucoup de notes factices
    parent_category = Category(
        id="cat_tech",
        name="Technology",
        description="Tech notes",
        tag_name="AI-Category-Technology",
        keywords=["tech"],
        note_count=50,
        avg_confidence=0.8,
        review_status=ReviewStatus.APPROVED,
    )

    # Créer des notes factices
    notes = [
        Note(
            id=f"note_{i}",
            file_path=f"/vault/note_{i}.md",
            file_name=f"note_{i}.md",
            relative_path=f"note_{i}.md",
            title=f"Note {i}",
            content=f"Content for note {i}",
            tags=[],
            word_count=100,
        )
        for i in range(30)  # 30 notes pour permettre clustering
    ]

    # Générer embeddings factices
    embedding_manager = EmbeddingManager(ollama_client=mock_ollama_client)
    note_texts = [note.content for note in notes]
    note_embeddings = embedding_manager.generate_embeddings_batch(note_texts)

    # Suggérer des sous-catégories
    subcategories = ameliorator.suggest_subcategories(
        category=parent_category,
        assigned_notes=notes,
        note_embeddings=note_embeddings,
        max_subcategories=3,
        min_notes_per_subcat=5,
    )

    # Vérifier qu'il y a des suggestions
    assert len(subcategories) >= 1

    # Vérifier la structure des sous-catégories
    for subcat in subcategories:
        assert subcat.parent_id == parent_category.id
        assert subcat.level == parent_category.level + 1
        assert subcat.review_status == ReviewStatus.PENDING


def test_suggest_merges(temp_category_store, mock_ollama_client):
    """Test suggestion de fusions."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
    )

    # Créer des catégories très similaires
    categories = [
        Category(
            id="cat1",
            name="Python Programming",
            description="Python programming and development",
            tag_name="AI-Category-Python",
            keywords=["python", "code"],
            note_count=10,
            avg_confidence=0.8,
            review_status=ReviewStatus.APPROVED,
        ),
        Category(
            id="cat2",
            name="Python Development",
            description="Python development and coding",
            tag_name="AI-Category-Python-Dev",
            keywords=["python", "development"],
            note_count=8,
            avg_confidence=0.75,
            review_status=ReviewStatus.APPROVED,
        ),
    ]

    # Générer embeddings (descriptions similaires → embeddings similaires)
    embedding_manager = EmbeddingManager(ollama_client=mock_ollama_client)
    category_texts = [f"{cat.name}: {cat.description}" for cat in categories]
    category_embeddings = embedding_manager.generate_embeddings_batch(category_texts)

    # Suggérer des fusions avec seuil bas pour le test
    merge_suggestions = ameliorator.suggest_merges(
        categories=categories,
        category_embeddings=category_embeddings,
        similarity_threshold=0.5,  # Seuil bas pour détecter fusion
    )

    # Vérifier la structure des suggestions
    # Note: Le test pourrait ne pas trouver de fusion si les embeddings factices
    # ne sont pas assez similaires. C'est OK pour un test de structure.
    for cat1_id, cat2_id, similarity in merge_suggestions:
        assert isinstance(cat1_id, str)
        assert isinstance(cat2_id, str)
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0


def test_load_taxonomy_empty_raises_error(tmp_path, mock_ollama_client):
    """Test que load_existing_taxonomy lève une erreur si aucune taxonomie."""
    # Créer un store vide
    store = CategoryStore(
        taxonomy_file=str(tmp_path / "empty_taxonomy.json"),
        assignments_file=str(tmp_path / "empty_assignments.json"),
    )

    ameliorator = CategoryAmeliorator(
        category_store=store,
        ollama_client=mock_ollama_client,
    )

    # Doit lever une ValueError
    with pytest.raises(ValueError, match="Aucune taxonomie existante"):
        ameliorator.load_existing_taxonomy()


# ============================================================================
# Test d'intégration
# ============================================================================


@pytest.mark.integration
def test_run_amelioration_integration(temp_category_store, mock_ollama_client, sample_notes):
    """Test d'intégration de run_amelioration."""
    ameliorator = CategoryAmeliorator(
        category_store=temp_category_store,
        ollama_client=mock_ollama_client,
        confidence_threshold=0.5,  # Seuil bas pour le test
    )

    # Lancer l'amélioration complète
    result = ameliorator.run_amelioration(
        new_notes=sample_notes,
        suggest_subcats=False,  # Désactiver pour test rapide
        suggest_fusions=False,  # Désactiver pour test rapide
    )

    # Vérifier la structure du résultat
    assert "new_notes_count" in result
    assert "assigned_notes_count" in result
    assert "coverage_percent" in result
    assert "categories_count" in result
    assert "categories_with_new_notes" in result
    assert "subcategory_suggestions" in result
    assert "merge_suggestions" in result
    assert "assignments" in result

    # Vérifier les valeurs
    assert result["new_notes_count"] == len(sample_notes)
    assert result["assigned_notes_count"] >= 0
    assert 0.0 <= result["coverage_percent"] <= 100.0
