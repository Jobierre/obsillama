"""
Tests pour FrontmatterWriter - Phase 5.1

Test du FrontmatterWriter avec pytest:
- Parsing avec ruamel.yaml
- Ajout de catégories et métadonnées AI
- Système de backup
- Gestion notes sans frontmatter
- Suppression métadonnées AI
"""

import pytest
import shutil
from pathlib import Path
from datetime import datetime

from obsillama.core.frontmatter_writer import FrontmatterWriter
from obsillama.models.category import Category, ReviewStatus


@pytest.fixture
def test_dir(tmp_path):
    """Crée un répertoire temporaire pour les tests."""
    return tmp_path


@pytest.fixture
def backup_dir(tmp_path):
    """Crée un répertoire de backup temporaire."""
    backup = tmp_path / "backups"
    backup.mkdir()
    return backup


@pytest.fixture
def writer(backup_dir):
    """Crée une instance de FrontmatterWriter."""
    return FrontmatterWriter(backup_dir=backup_dir)


@pytest.fixture
def note_with_frontmatter(test_dir):
    """Crée une note de test avec frontmatter."""
    note_path = test_dir / "test_note.md"
    content = """---
title: Ma Note de Test
tags:
  - test
  - obsidian
author: Jobierre
created: 2026-01-11
---

# Ma Note de Test

Ceci est le contenu de ma note.
Elle contient plusieurs paragraphes.

## Section 2

Plus de contenu ici.
"""
    note_path.write_text(content, encoding="utf-8")
    return note_path


@pytest.fixture
def note_without_frontmatter(test_dir):
    """Crée une note de test sans frontmatter."""
    note_path = test_dir / "test_note_no_fm.md"
    content = """# Ma Note Sans Frontmatter

Ceci est une note simple sans frontmatter.
Juste du contenu markdown.
"""
    note_path.write_text(content, encoding="utf-8")
    return note_path


@pytest.fixture
def test_categories():
    """Crée des catégories de test."""
    cat1 = Category(
        id="cat_001",
        name="Développement Python",
        description="Notes sur le développement Python",
        tag_name="développement_python",
        note_count=5,
        avg_confidence=0.85
    )
    return [cat1]


class TestFrontmatterWriterParsing:
    """Tests de parsing du frontmatter."""

    def test_parse_note_file_with_frontmatter(self, writer, note_with_frontmatter):
        """Test: Parser une note avec frontmatter."""
        frontmatter, content, raw = writer.parse_note_file(note_with_frontmatter)

        assert "title" in frontmatter
        assert frontmatter["title"] == "Ma Note de Test"
        assert "tags" in frontmatter
        assert isinstance(frontmatter["tags"], list)
        assert "test" in frontmatter["tags"]
        assert "# Ma Note de Test" in content

    def test_parse_note_file_without_frontmatter(self, writer, note_without_frontmatter):
        """Test: Parser une note sans frontmatter."""
        frontmatter, content, raw = writer.parse_note_file(note_without_frontmatter)

        assert len(frontmatter) == 0
        assert "# Ma Note Sans Frontmatter" in content

    def test_parse_nonexistent_file(self, writer, test_dir):
        """Test: Erreur si le fichier n'existe pas."""
        with pytest.raises(FileNotFoundError):
            writer.parse_note_file(test_dir / "nonexistent.md")


class TestFrontmatterWriterUpdate:
    """Tests de mise à jour du frontmatter."""

    def test_update_frontmatter_adds_ai_metadata(
        self, writer, note_with_frontmatter, test_categories
    ):
        """Test: Mise à jour ajoute les métadonnées AI."""
        confidence = 0.85

        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            confidence,
            backup=True
        )

        # Vérifier les changements
        frontmatter, _, _ = writer.parse_note_file(note_with_frontmatter)

        # Vérifier ai_categories
        assert "ai_categories" in frontmatter
        assert "Développement Python" in frontmatter["ai_categories"]

        # Vérifier ai_confidence
        assert "ai_confidence" in frontmatter
        assert frontmatter["ai_confidence"] == 0.85

        # Vérifier ai_processed_date
        assert "ai_processed_date" in frontmatter
        # Valider format ISO 8601
        datetime.fromisoformat(frontmatter["ai_processed_date"])

    def test_update_frontmatter_merges_tags(
        self, writer, note_with_frontmatter, test_categories
    ):
        """Test: Les tags AI sont mergés avec les tags existants."""
        # Tags avant
        fm_before, _, _ = writer.parse_note_file(note_with_frontmatter)
        tags_before = fm_before.get("tags", [])
        assert "test" in tags_before

        # Mise à jour
        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            0.85,
            backup=False
        )

        # Tags après
        fm_after, _, _ = writer.parse_note_file(note_with_frontmatter)
        tags_after = fm_after.get("tags", [])

        # Vérifier que les anciens tags sont préservés
        assert "test" in tags_after
        assert "obsidian" in tags_after

        # Vérifier que les nouveaux tags AI sont ajoutés (case insensitive)
        ai_tags = [t for t in tags_after if "ai-category-" in str(t).lower()]
        assert len(ai_tags) > 0

    def test_update_frontmatter_preserves_content(
        self, writer, note_with_frontmatter, test_categories
    ):
        """Test: Le contenu markdown est préservé après mise à jour."""
        # Contenu avant
        _, content_before, _ = writer.parse_note_file(note_with_frontmatter)

        # Mise à jour
        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            0.85,
            backup=False
        )

        # Contenu après
        _, content_after, _ = writer.parse_note_file(note_with_frontmatter)

        # Le contenu markdown devrait être identique
        assert content_before == content_after
        assert "# Ma Note de Test" in content_after
        assert "## Section 2" in content_after


class TestFrontmatterWriterBackup:
    """Tests du système de backup."""

    def test_backup_creates_snapshot(self, writer, note_with_frontmatter, backup_dir):
        """Test: Un backup crée un snapshot avec timestamp."""
        backup_path = writer.backup_note(note_with_frontmatter)

        assert backup_path.exists()
        assert backup_path.parent.parent == backup_dir
        assert backup_path.name == note_with_frontmatter.name

    def test_backup_preserves_content(self, writer, note_with_frontmatter):
        """Test: Le backup contient le contenu original."""
        # Contenu original
        original_content = note_with_frontmatter.read_text(encoding="utf-8")

        # Créer backup
        backup_path = writer.backup_note(note_with_frontmatter)

        # Contenu du backup
        backup_content = backup_path.read_text(encoding="utf-8")

        assert original_content == backup_content

    def test_update_with_backup_creates_snapshot(
        self, writer, note_with_frontmatter, test_categories, backup_dir
    ):
        """Test: update_frontmatter avec backup=True crée un snapshot."""
        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            0.85,
            backup=True
        )

        # Vérifier qu'un snapshot existe
        snapshots = list(backup_dir.iterdir())
        assert len(snapshots) > 0

        # Vérifier qu'il contient le fichier
        snapshot = snapshots[0]
        backup_files = list(snapshot.glob("*.md"))
        assert len(backup_files) > 0


class TestFrontmatterWriterNoFrontmatter:
    """Tests pour notes sans frontmatter."""

    def test_update_creates_frontmatter(
        self, writer, note_without_frontmatter, test_categories
    ):
        """Test: Mise à jour crée un frontmatter si absent."""
        writer.update_frontmatter(
            note_without_frontmatter,
            test_categories,
            0.75,
            backup=False
        )

        frontmatter, content, _ = writer.parse_note_file(note_without_frontmatter)

        # Vérifier que le frontmatter a été créé
        assert "ai_categories" in frontmatter
        assert "ai_confidence" in frontmatter
        assert frontmatter["ai_confidence"] == 0.75

        # Vérifier que le contenu est préservé
        assert "# Ma Note Sans Frontmatter" in content


class TestFrontmatterWriterCleanup:
    """Tests de suppression des métadonnées AI."""

    def test_remove_ai_metadata(
        self, writer, note_with_frontmatter, test_categories
    ):
        """Test: remove_ai_metadata supprime toutes les métadonnées AI."""
        # Ajouter des métadonnées AI
        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            0.9,
            backup=False
        )

        # Vérifier qu'elles sont présentes
        fm_before, _, _ = writer.parse_note_file(note_with_frontmatter)
        assert "ai_categories" in fm_before
        assert "ai_confidence" in fm_before
        assert "ai_processed_date" in fm_before

        # Supprimer
        writer.remove_ai_metadata(note_with_frontmatter, backup=False)

        # Vérifier qu'elles sont supprimées
        fm_after, _, _ = writer.parse_note_file(note_with_frontmatter)
        assert "ai_categories" not in fm_after
        assert "ai_confidence" not in fm_after
        assert "ai_processed_date" not in fm_after

    def test_remove_ai_metadata_removes_ai_tags(
        self, writer, note_with_frontmatter, test_categories
    ):
        """Test: remove_ai_metadata supprime les tags AI-Category-*."""
        # Ajouter des métadonnées AI
        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            0.9,
            backup=False
        )

        # Supprimer
        writer.remove_ai_metadata(note_with_frontmatter, backup=False)

        # Vérifier que les tags AI sont supprimés
        fm_after, _, _ = writer.parse_note_file(note_with_frontmatter)
        tags = fm_after.get("tags", [])
        ai_tags = [t for t in tags if "AI-Category-" in str(t)]
        assert len(ai_tags) == 0

    def test_remove_ai_metadata_preserves_other_tags(
        self, writer, note_with_frontmatter, test_categories
    ):
        """Test: remove_ai_metadata préserve les tags non-AI."""
        # Ajouter des métadonnées AI
        writer.update_frontmatter(
            note_with_frontmatter,
            test_categories,
            0.9,
            backup=False
        )

        # Supprimer
        writer.remove_ai_metadata(note_with_frontmatter, backup=False)

        # Vérifier que les tags originaux sont préservés
        fm_after, _, _ = writer.parse_note_file(note_with_frontmatter)
        tags = fm_after.get("tags", [])
        assert "test" in tags
        assert "obsidian" in tags
