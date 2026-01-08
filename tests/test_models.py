"""
Tests pour les modèles de données ObsIllama

Ce module teste tous les modèles Pydantic: Note, Category, Embedding, GraphEntity, etc.
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest
import numpy as np

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from obsillama.models.note import Note
from obsillama.models.category import Category, ReviewStatus
from obsillama.models.embedding import Embedding
from obsillama.models.graph_entity import (
    GraphEntity,
    GraphRelationship,
    GraphCommunity,
    EntityType,
    RelationshipType,
)


# =============================================================================
# Tests du modèle Note
# =============================================================================


def test_note_creation():
    """Test la création d'une note minimale"""
    note = Note(
        id="note_001",
        file_path="/vault/test.md",
        file_name="test.md",
        relative_path="test.md",
        title="Test Note",
    )

    assert note.id == "note_001"
    assert note.title == "Test Note"
    assert note.word_count == 0
    assert note.tags == []


def test_note_with_full_data():
    """Test la création d'une note avec toutes les données"""
    note = Note(
        id="note_002",
        file_path="/vault/project/note.md",
        file_name="note.md",
        relative_path="project/note.md",
        title="Complete Note",
        content="This is the content of the note",
        tags=["tag1", "tag2"],
        frontmatter_tags=["meta1"],
        inline_tags=["#inline"],
        word_count=6,
        ai_categories=["Technology"],
        ai_confidence=0.85,
    )

    assert note.title == "Complete Note"
    assert len(note.tags) == 2
    assert note.ai_confidence == 0.85


def test_note_tag_normalization():
    """Test la normalisation des tags"""
    note = Note(
        id="note_003",
        file_path="/vault/test.md",
        file_name="test.md",
        relative_path="test.md",
        title="Tag Test",
        tags=["#Tag1", "TAG2", " tag3 "],
    )

    # Les tags doivent être en lowercase et sans #
    assert "tag1" in note.tags
    assert "tag2" in note.tags
    assert "tag3" in note.tags


def test_note_get_all_tags():
    """Test la méthode get_all_tags()"""
    note = Note(
        id="note_004",
        file_path="/vault/test.md",
        file_name="test.md",
        relative_path="test.md",
        title="Tags Test",
        tags=["general"],
        frontmatter_tags=["front"],
        inline_tags=["inline"],
    )

    all_tags = note.get_all_tags()
    assert "general" in all_tags
    assert "front" in all_tags
    assert "inline" in all_tags
    assert len(all_tags) == 3


def test_note_has_tag():
    """Test la méthode has_tag()"""
    note = Note(
        id="note_005",
        file_path="/vault/test.md",
        file_name="test.md",
        relative_path="test.md",
        title="Has Tag Test",
        tags=["python", "coding"],
    )

    assert note.has_tag("python")
    assert note.has_tag("#Python")  # Case-insensitive et avec #
    assert not note.has_tag("javascript")


def test_note_validation_empty_title():
    """Test la validation d'un titre vide"""
    with pytest.raises(ValueError, match="titre ne peut pas être vide"):
        Note(
            id="note_006",
            file_path="/vault/test.md",
            file_name="test.md",
            relative_path="test.md",
            title="",  # Titre vide
        )


# =============================================================================
# Tests du modèle Category
# =============================================================================


def test_category_creation():
    """Test la création d'une catégorie minimale"""
    category = Category(
        id="cat_001", name="Technology", tag_name="AI-Category-Technology"
    )

    assert category.id == "cat_001"
    assert category.name == "Technology"
    assert category.review_status == ReviewStatus.PENDING
    assert category.level == 0


def test_category_with_hierarchy():
    """Test la création d'une catégorie avec hiérarchie"""
    parent = Category(id="cat_parent", name="Parent", tag_name="AI-Category-Parent")

    child = Category(
        id="cat_child",
        name="Child",
        tag_name="AI-Category-Child",
        parent_id="cat_parent",
        level=1,
    )

    assert child.parent_id == "cat_parent"
    assert child.is_subcategory()
    assert not child.is_root_category()
    assert parent.is_root_category()


def test_category_approval():
    """Test l'approbation d'une catégorie"""
    category = Category(id="cat_002", name="Test", tag_name="AI-Category-Test")

    assert category.needs_review()
    assert not category.is_approved()

    category.approve(reviewer="user")

    assert category.is_approved()
    assert not category.needs_review()
    assert category.reviewed_by == "user"
    assert category.reviewed_at is not None


def test_category_rejection():
    """Test le rejet d'une catégorie"""
    category = Category(id="cat_003", name="Test", tag_name="AI-Category-Test")

    category.reject(reviewer="admin")

    assert category.review_status == ReviewStatus.REJECTED
    assert category.reviewed_by == "admin"


def test_category_update_stats():
    """Test la mise à jour des statistiques"""
    category = Category(id="cat_004", name="Test", tag_name="AI-Category-Test")

    assert category.version == 1

    category.update_stats(note_count=10, avg_confidence=0.8)

    assert category.note_count == 10
    assert category.avg_confidence == 0.8
    assert category.version == 2


def test_category_tag_normalization():
    """Test la normalisation du tag_name"""
    category = Category(
        id="cat_005", name="My Category", tag_name="My Category"  # Avec espaces
    )

    # Le tag doit être normalisé (lowercase, tirets au lieu d'espaces)
    assert category.tag_name == "my-category"


def test_category_color_validation():
    """Test la validation de la couleur"""
    # Couleur valide
    category = Category(
        id="cat_006", name="Test", tag_name="AI-Category-Test", color="#FF5733"
    )
    assert category.color == "#FF5733"

    # Couleur sans # (ajouté automatiquement)
    category2 = Category(
        id="cat_007", name="Test2", tag_name="AI-Category-Test2", color="00FF00"
    )
    assert category2.color == "#00FF00"

    # Couleur invalide
    with pytest.raises(ValueError, match="Couleur invalide"):
        Category(
            id="cat_008", name="Test3", tag_name="AI-Category-Test3", color="#FFF"  # Trop court
        )


# =============================================================================
# Tests du modèle Embedding
# =============================================================================


def test_embedding_creation():
    """Test la création d'un embedding"""
    vector = [0.1, 0.2, 0.3]
    embedding = Embedding(
        id="emb_001",
        source_id="note_001",
        source_type="note",
        vector=vector,
        model_dimension=3,
        content_hash="abc123",
    )

    assert embedding.id == "emb_001"
    assert len(embedding.vector) == 3
    assert embedding.model_dimension == 3
    assert embedding.norm is not None


def test_embedding_dimension_validation():
    """Test la validation de la dimension"""
    # Dimension correcte
    embedding = Embedding(
        id="emb_002",
        source_id="note_002",
        source_type="note",
        vector=[1.0, 2.0],
        model_dimension=2,
        content_hash="xyz",
    )
    assert len(embedding.vector) == embedding.model_dimension

    # Dimension incorrecte
    with pytest.raises(ValueError, match="dimension du vecteur"):
        Embedding(
            id="emb_003",
            source_id="note_003",
            source_type="note",
            vector=[1.0, 2.0, 3.0],
            model_dimension=2,  # Ne correspond pas à la taille du vecteur
            content_hash="xyz",
        )


def test_embedding_normalize():
    """Test la normalisation du vecteur"""
    embedding = Embedding(
        id="emb_004",
        source_id="note_004",
        source_type="note",
        vector=[3.0, 4.0],  # Norme = 5.0
        model_dimension=2,
        content_hash="hash",
    )

    normalized = embedding.normalize()

    assert normalized.is_normalized
    assert abs(normalized.norm - 1.0) < 1e-6  # Norme = 1


def test_embedding_cosine_similarity():
    """Test le calcul de similarité cosinus"""
    emb1 = Embedding(
        id="emb_005",
        source_id="note_005",
        source_type="note",
        vector=[1.0, 0.0, 0.0],
        model_dimension=3,
        content_hash="h1",
    )

    emb2 = Embedding(
        id="emb_006",
        source_id="note_006",
        source_type="note",
        vector=[1.0, 0.0, 0.0],  # Identique
        model_dimension=3,
        content_hash="h2",
    )

    emb3 = Embedding(
        id="emb_007",
        source_id="note_007",
        source_type="note",
        vector=[0.0, 1.0, 0.0],  # Orthogonal
        model_dimension=3,
        content_hash="h3",
    )

    # Vecteurs identiques → similarité = 1.0
    assert abs(emb1.cosine_similarity(emb2) - 1.0) < 1e-6

    # Vecteurs orthogonaux → similarité = 0.0
    assert abs(emb1.cosine_similarity(emb3)) < 1e-6


def test_embedding_euclidean_distance():
    """Test le calcul de distance euclidienne"""
    emb1 = Embedding(
        id="emb_008",
        source_id="note_008",
        source_type="note",
        vector=[0.0, 0.0],
        model_dimension=2,
        content_hash="h1",
    )

    emb2 = Embedding(
        id="emb_009",
        source_id="note_009",
        source_type="note",
        vector=[3.0, 4.0],
        model_dimension=2,
        content_hash="h2",
    )

    distance = emb1.euclidean_distance(emb2)
    assert abs(distance - 5.0) < 1e-6  # Distance = 5


# =============================================================================
# Tests des modèles GraphRAG
# =============================================================================


def test_graph_entity_creation():
    """Test la création d'une entité"""
    entity = GraphEntity(
        id="ent_001", name="Python", type=EntityType.TECHNOLOGY, description="Programming language"
    )

    assert entity.id == "ent_001"
    assert entity.name == "Python"
    assert entity.type == EntityType.TECHNOLOGY
    assert entity.mention_count == 0


def test_graph_entity_add_mention():
    """Test l'ajout de mentions"""
    entity = GraphEntity(id="ent_002", name="Docker", type=EntityType.TOOL)

    entity.add_mention("note_001", context="Using Docker for deployment")
    entity.add_mention("note_002")

    assert entity.mention_count == 2
    assert "note_001" in entity.source_note_ids
    assert len(entity.context_snippets) == 1


def test_graph_relationship_creation():
    """Test la création d'une relation"""
    rel = GraphRelationship(
        id="rel_001",
        source_entity_id="ent_python",
        target_entity_id="ent_django",
        relationship_type=RelationshipType.USES,
    )

    assert rel.source_entity_id == "ent_python"
    assert rel.target_entity_id == "ent_django"
    assert rel.relationship_type == RelationshipType.USES


def test_graph_community_creation():
    """Test la création d'une communauté"""
    community = GraphCommunity(
        id="com_001",
        name="Programming Community",
        entity_ids=["ent_001", "ent_002", "ent_003"],
    )

    assert community.id == "com_001"
    assert community.entity_count == 3
    assert len(community.entity_ids) == 3


def test_graph_community_add_entity():
    """Test l'ajout d'une entité à une communauté"""
    community = GraphCommunity(id="com_002", entity_ids=["ent_001"])

    assert community.entity_count == 1

    community.add_entity("ent_002")

    assert community.entity_count == 2
    assert "ent_002" in community.entity_ids


def test_graph_community_density():
    """Test le calcul de densité"""
    community = GraphCommunity(
        id="com_003",
        entity_ids=["e1", "e2", "e3"],  # 3 entités
        internal_edges=3,  # Maximum possible = 3
    )

    density = community.calculate_density()

    assert density == 1.0  # Toutes les connexions possibles


# =============================================================================
# Tests d'intégration
# =============================================================================


def test_models_to_dict_from_dict():
    """Test la sérialisation/désérialisation de tous les modèles"""

    # Note
    note = Note(
        id="test", file_path="/test", file_name="test.md", relative_path="test.md", title="Test"
    )
    note_dict = note.to_dict()
    note_restored = Note.from_dict(note_dict)
    assert note_restored.id == note.id

    # Category
    category = Category(id="test", name="Test", tag_name="test")
    cat_dict = category.to_dict()
    cat_restored = Category.from_dict(cat_dict)
    assert cat_restored.id == category.id

    # GraphEntity
    entity = GraphEntity(id="test", name="Test", type=EntityType.CONCEPT)
    ent_dict = entity.to_dict()
    ent_restored = GraphEntity.from_dict(ent_dict)
    assert ent_restored.id == entity.id


# =============================================================================
# Script principal
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
