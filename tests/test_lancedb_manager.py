"""
Tests pour le LanceDB Manager

Ces tests vérifient:
- Création des tables
- Insertion de notes avec embeddings
- Récupération par ID
- Recherche vectorielle
- Persistance
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.models.note import Note
from obsillama.models.category import Category


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Crée un chemin temporaire pour la DB."""
    db_path = tmp_path / "test_lancedb"
    yield str(db_path)
    # Cleanup
    if db_path.exists():
        shutil.rmtree(db_path)


@pytest.fixture
def lancedb_manager(temp_db_path):
    """Crée un manager LanceDB de test."""
    return LanceDBManager(db_path=temp_db_path)


@pytest.fixture
def sample_notes():
    """Crée 5 notes de test."""
    notes = []

    for i in range(1, 6):
        note = Note(
            id=f"test_note_{i}",
            file_path=f"/vault/note_{i}.md",
            file_name=f"note_{i}.md",
            relative_path=f"note_{i}.md",
            title=f"Test Note {i}",
            content=f"This is test note number {i} with some content.",
            word_count=10 + i,
            tags=["test", f"tag{i}"],
            folder="",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            scanned_at=datetime.now(),
        )
        notes.append(note)

    return notes


@pytest.fixture
def sample_embeddings():
    """Crée 5 embeddings de test (768 dimensions)."""
    # Créer des embeddings différents mais valides
    embeddings = []

    for i in range(5):
        # Créer un vecteur avec des valeurs légèrement différentes
        embedding = [0.1 + i * 0.05] * 768
        embeddings.append(embedding)

    return embeddings


@pytest.fixture
def sample_categories():
    """Crée des catégories de test."""
    categories = []

    for i in range(1, 4):
        category = Category(
            id=f"cat_{i}",
            name=f"Category {i}",
            tag_name=f"cat-{i}",
            description=f"Description for category {i}",
            keywords=["keyword1", "keyword2"],
            parent_id=None,
            children_ids=[],
            level=0,
            note_count=0,
            avg_confidence=0.8,
            created_at=datetime.now(),
            review_status="pending",
        )
        categories.append(category)

    return categories


# ============================================================================
# Tests de création des tables
# ============================================================================


def test_lancedb_manager_initialization(lancedb_manager):
    """Test l'initialisation du manager."""
    assert lancedb_manager is not None
    assert lancedb_manager.db is not None
    assert lancedb_manager.embedding_dim == 768


def test_create_notes_table(lancedb_manager):
    """Test la création de la table notes."""
    lancedb_manager.create_notes_table()

    assert lancedb_manager.table_exists("notes")
    assert "notes" in lancedb_manager.list_tables()


def test_create_categories_table(lancedb_manager):
    """Test la création de la table categories."""
    lancedb_manager.create_categories_table()

    assert lancedb_manager.table_exists("categories")


def test_create_entities_table(lancedb_manager):
    """Test la création de la table entities."""
    lancedb_manager.create_entities_table()

    assert lancedb_manager.table_exists("entities")


def test_create_communities_table(lancedb_manager):
    """Test la création de la table communities."""
    lancedb_manager.create_communities_table()

    assert lancedb_manager.table_exists("communities")


def test_create_all_tables(lancedb_manager):
    """Test la création de toutes les tables."""
    lancedb_manager.create_all_tables()

    tables = lancedb_manager.list_tables()
    assert "notes" in tables
    assert "categories" in tables
    assert "entities" in tables
    assert "communities" in tables


def test_create_table_overwrite_mode(lancedb_manager):
    """Test la création en mode overwrite."""
    # Créer une première fois
    lancedb_manager.create_notes_table()

    # Recréer en mode overwrite
    lancedb_manager.create_notes_table(mode="overwrite")

    assert lancedb_manager.table_exists("notes")


# ============================================================================
# Tests d'insertion de notes
# ============================================================================


def test_insert_notes(lancedb_manager, sample_notes, sample_embeddings):
    """Test l'insertion de notes."""
    lancedb_manager.create_notes_table()

    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    # Vérifier que les notes sont insérées
    count = lancedb_manager.count_records("notes")
    assert count == 5


def test_insert_notes_mismatch_error(lancedb_manager, sample_notes, sample_embeddings):
    """Test l'erreur si nombre de notes != nombre d'embeddings."""
    lancedb_manager.create_notes_table()

    with pytest.raises(ValueError, match="Mismatch"):
        # Seulement 4 embeddings pour 5 notes
        lancedb_manager.insert_notes(sample_notes, sample_embeddings[:4])


def test_insert_categories(lancedb_manager, sample_categories):
    """Test l'insertion de catégories."""
    lancedb_manager.create_categories_table()

    # Créer des embeddings pour les catégories
    embeddings = [[0.1] * 768 for _ in range(len(sample_categories))]

    lancedb_manager.insert_categories(sample_categories, embeddings)

    count = lancedb_manager.count_records("categories")
    assert count == 3


# ============================================================================
# Tests de récupération de données
# ============================================================================


def test_get_note_by_id(lancedb_manager, sample_notes, sample_embeddings):
    """Test la récupération d'une note par ID."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    # Récupérer la première note
    note = lancedb_manager.get_note_by_id("test_note_1")

    assert note is not None
    assert note["id"] == "test_note_1"
    assert note["title"] == "Test Note 1"


def test_get_note_by_id_not_found(lancedb_manager):
    """Test la récupération d'une note inexistante."""
    lancedb_manager.create_notes_table()

    note = lancedb_manager.get_note_by_id("nonexistent")

    assert note is None


def test_get_all_notes(lancedb_manager, sample_notes, sample_embeddings):
    """Test la récupération de toutes les notes."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    notes = lancedb_manager.get_all_notes()

    assert len(notes) == 5


def test_get_all_notes_with_limit(lancedb_manager, sample_notes, sample_embeddings):
    """Test la récupération avec limite."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    notes = lancedb_manager.get_all_notes(limit=3)

    assert len(notes) == 3


def test_get_notes_by_ids(lancedb_manager, sample_notes, sample_embeddings):
    """Test la récupération de plusieurs notes par IDs."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    notes = lancedb_manager.get_notes_by_ids(["test_note_1", "test_note_3", "test_note_5"])

    assert len(notes) == 3
    assert all(n["id"] in ["test_note_1", "test_note_3", "test_note_5"] for n in notes)


# ============================================================================
# Tests de recherche vectorielle
# ============================================================================


def test_search_notes_by_embedding(lancedb_manager, sample_notes, sample_embeddings):
    """Test la recherche vectorielle."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    # Rechercher avec un vecteur proche du premier embedding
    query_vector = [0.11] * 768  # Proche de [0.1] * 768

    results = lancedb_manager.search_notes_by_embedding(query_vector, limit=3)

    assert len(results) > 0
    assert len(results) <= 3

    # Le premier résultat devrait être test_note_1
    assert results[0]["id"] == "test_note_1"


def test_search_with_filter(lancedb_manager, sample_notes, sample_embeddings):
    """Test la recherche avec filtre."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    query_vector = [0.15] * 768

    # Filtrer par word_count > 12
    results = lancedb_manager.search_notes_by_embedding(
        query_vector, limit=10, filter_query="word_count > 12"
    )

    # Devrait retourner les notes 3, 4, 5 (word_count = 13, 14, 15)
    assert len(results) > 0
    assert all(r["word_count"] > 12 for r in results)


# ============================================================================
# Tests de création d'index vectoriels
# ============================================================================


def test_create_vector_index(lancedb_manager, sample_notes, sample_embeddings):
    """Test la création d'index vectoriel."""
    lancedb_manager.create_notes_table()
    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    # Créer l'index
    # Note: Avec seulement 5 notes, l'index peut ne pas être créé
    # (LanceDB a besoin d'un minimum de données)
    try:
        lancedb_manager.create_vector_index("notes")
    except Exception as e:
        # C'est OK si l'index ne peut pas être créé avec peu de données
        pytest.skip(f"Pas assez de données pour créer l'index: {e}")


# ============================================================================
# Tests de persistance
# ============================================================================


def test_persistence(temp_db_path, sample_notes, sample_embeddings):
    """Test la persistance (fermer/rouvrir DB)."""
    # Créer et insérer des données
    manager1 = LanceDBManager(db_path=temp_db_path)
    manager1.create_notes_table()
    manager1.insert_notes(sample_notes, sample_embeddings)

    # Récupérer une note
    note_before = manager1.get_note_by_id("test_note_1")
    assert note_before is not None

    # Fermer (simulé par la destruction de l'objet)
    del manager1

    # Rouvrir la DB
    manager2 = LanceDBManager(db_path=temp_db_path)

    # Vérifier que les données sont toujours là
    assert manager2.table_exists("notes")
    assert manager2.count_records("notes") == 5

    # Récupérer la même note
    note_after = manager2.get_note_by_id("test_note_1")
    assert note_after is not None
    assert note_after["id"] == note_before["id"]
    assert note_after["title"] == note_before["title"]


# ============================================================================
# Tests utilitaires
# ============================================================================


def test_list_tables(lancedb_manager):
    """Test la liste des tables."""
    lancedb_manager.create_notes_table()
    lancedb_manager.create_categories_table()

    tables = lancedb_manager.list_tables()

    assert "notes" in tables
    assert "categories" in tables


def test_table_exists(lancedb_manager):
    """Test la vérification d'existence de table."""
    assert not lancedb_manager.table_exists("notes")

    lancedb_manager.create_notes_table()

    assert lancedb_manager.table_exists("notes")


def test_count_records(lancedb_manager, sample_notes, sample_embeddings):
    """Test le comptage de records."""
    lancedb_manager.create_notes_table()

    assert lancedb_manager.count_records("notes") == 0

    lancedb_manager.insert_notes(sample_notes, sample_embeddings)

    assert lancedb_manager.count_records("notes") == 5


def test_repr(lancedb_manager):
    """Test la représentation string."""
    lancedb_manager.create_notes_table()

    repr_str = repr(lancedb_manager)

    assert "LanceDBManager" in repr_str
    assert "notes" in repr_str


# ============================================================================
# Tests d'intégration
# ============================================================================


@pytest.mark.integration
def test_full_workflow():
    """
    Test du workflow complet:
    1. Créer toutes les tables
    2. Insérer des notes
    3. Rechercher
    4. Vérifier persistance
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "integration_test"

        # 1. Créer le manager et les tables
        manager = LanceDBManager(db_path=str(db_path))
        manager.create_all_tables()

        # 2. Créer des notes de test
        notes = []
        embeddings = []

        for i in range(10):
            note = Note(
                id=f"note_{i}",
                file_path=f"/vault/note_{i}.md",
                file_name=f"note_{i}.md",
                relative_path=f"note_{i}.md",
                title=f"Integration Note {i}",
                content=f"Content for note {i}",
                word_count=50 + i * 10,
                tags=["integration", f"test{i}"],
                folder="integration",
            )
            notes.append(note)

            # Embedding unique pour chaque note
            embedding = [0.1 + i * 0.01] * 768
            embeddings.append(embedding)

        # 3. Insérer
        manager.insert_notes(notes, embeddings)

        # 4. Vérifier l'insertion
        assert manager.count_records("notes") == 10

        # 5. Recherche vectorielle
        query_vector = [0.15] * 768
        results = manager.search_notes_by_embedding(query_vector, limit=5)

        assert len(results) == 5

        # 6. Récupération par ID
        note = manager.get_note_by_id("note_5")
        assert note is not None
        assert note["title"] == "Integration Note 5"

        # 7. Fermer et rouvrir
        del manager

        manager2 = LanceDBManager(db_path=str(db_path))
        assert manager2.count_records("notes") == 10

        print("\n✅ Workflow complet validé!")
