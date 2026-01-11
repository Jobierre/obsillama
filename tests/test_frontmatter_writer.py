"""
Tests pour FrontmatterWriter - ObsIllama

Ce module teste l'écriture et la modification du frontmatter YAML dans les notes Obsidian.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from obsillama.core.frontmatter_writer import FrontmatterWriter
from obsillama.models.category import Category
from obsillama.models.note import Note


@pytest.fixture
def temp_dir():
    """Crée un dossier temporaire pour les tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup après les tests
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def writer(temp_dir):
    """Crée un FrontmatterWriter avec backup dans le dossier temporaire."""
    backup_dir = temp_dir / "backups"
    return FrontmatterWriter(backup_dir=backup_dir)


@pytest.fixture
def sample_note_with_frontmatter(temp_dir):
    """Crée une note de test avec frontmatter."""
    content = """---
title: Test Note
tags:
  - existing-tag
  - another-tag
author: Jobierre
date: 2026-01-11
---

# Test Content

This is a test note with some content.

## Section 1

- Item 1
- Item 2

[[linked-note]]
"""
    note_path = temp_dir / "test_note.md"
    note_path.write_text(content, encoding="utf-8")
    return note_path


@pytest.fixture
def sample_note_without_frontmatter(temp_dir):
    """Crée une note de test sans frontmatter."""
    content = """# Test Note Without Frontmatter

This note has no frontmatter, just pure markdown content.

## Some Section

Content here.
"""
    note_path = temp_dir / "note_no_frontmatter.md"
    note_path.write_text(content, encoding="utf-8")
    return note_path


@pytest.fixture
def sample_note_malformed_frontmatter(temp_dir):
    """Crée une note avec frontmatter malformé (YAML invalide)."""
    content = """---
title: Test
tags: [unclosed list
invalid: : yaml
---

Content here.
"""
    note_path = temp_dir / "note_malformed.md"
    note_path.write_text(content, encoding="utf-8")
    return note_path


@pytest.fixture
def sample_categories():
    """Crée des catégories de test."""
    return [
        Category(
            id="cat1",
            name="Développement Web",
            tag_name="dev-web",
            description="Notes sur le développement web",
            level=0,
            review_status="approved"
        ),
        Category(
            id="cat2",
            name="Python",
            tag_name="python",
            description="Notes sur Python",
            level=0,
            review_status="approved"
        )
    ]


# ─────────────────────────────────────────────────────────────────
# Tests d'initialisation
# ─────────────────────────────────────────────────────────────────

def test_writer_initialization(temp_dir):
    """Test l'initialisation du FrontmatterWriter."""
    backup_dir = temp_dir / "custom_backup"
    writer = FrontmatterWriter(backup_dir=backup_dir)

    assert writer.backup_dir == backup_dir
    assert writer.yaml is not None
    assert writer.yaml.preserve_quotes is True
    assert writer.yaml.default_flow_style is False


def test_writer_default_backup_dir():
    """Test l'initialisation avec backup_dir par défaut."""
    writer = FrontmatterWriter()

    assert writer.backup_dir == Path(".obsillama_backups")


# ─────────────────────────────────────────────────────────────────
# Tests de parsing
# ─────────────────────────────────────────────────────────────────

def test_parse_note_with_frontmatter(writer, sample_note_with_frontmatter):
    """Test le parsing d'une note avec frontmatter."""
    frontmatter, content, raw = writer.parse_note_file(sample_note_with_frontmatter)

    # Vérifier le frontmatter parsé
    assert "title" in frontmatter
    assert frontmatter["title"] == "Test Note"
    assert "tags" in frontmatter
    assert "existing-tag" in frontmatter["tags"]
    assert frontmatter["author"] == "Jobierre"

    # Vérifier le contenu (sans frontmatter)
    assert "# Test Content" in content
    assert "---" not in content  # Le frontmatter est bien retiré
    assert "[[linked-note]]" in content


def test_parse_note_without_frontmatter(writer, sample_note_without_frontmatter):
    """Test le parsing d'une note sans frontmatter."""
    frontmatter, content, raw = writer.parse_note_file(sample_note_without_frontmatter)

    # Pas de frontmatter → dict vide
    assert len(frontmatter) == 0

    # Le contenu est intact
    assert "# Test Note Without Frontmatter" in content
    assert content == raw


def test_parse_note_malformed_yaml(writer, sample_note_malformed_frontmatter):
    """Test le parsing d'une note avec YAML invalide."""
    # Le YAML invalide devrait lever une ValueError
    with pytest.raises(ValueError, match="YAML invalide"):
        writer.parse_note_file(sample_note_malformed_frontmatter)


def test_parse_note_file_not_found(writer, temp_dir):
    """Test le parsing d'un fichier qui n'existe pas."""
    non_existent = temp_dir / "does_not_exist.md"

    with pytest.raises(FileNotFoundError):
        writer.parse_note_file(non_existent)


# ─────────────────────────────────────────────────────────────────
# Tests de backup
# ─────────────────────────────────────────────────────────────────

def test_backup_note_creates_snapshot(writer, sample_note_with_frontmatter):
    """Test que le backup crée bien un snapshot avec timestamp."""
    backup_path = writer.backup_note(sample_note_with_frontmatter)

    # Vérifier que le backup existe
    assert backup_path.exists()

    # Vérifier la structure: backups/YYYYMMDD_HHMMSS/test_note.md
    assert backup_path.parent.parent == writer.backup_dir
    assert backup_path.name == sample_note_with_frontmatter.name

    # Vérifier que le contenu est identique
    original_content = sample_note_with_frontmatter.read_text(encoding="utf-8")
    backup_content = backup_path.read_text(encoding="utf-8")
    assert original_content == backup_content


def test_backup_preserves_multiple_snapshots(writer, sample_note_with_frontmatter):
    """Test que plusieurs backups créent des snapshots séparés."""
    import time

    # Créer 2 backups avec 1 seconde d'écart
    backup1 = writer.backup_note(sample_note_with_frontmatter)
    time.sleep(1.1)  # Attendre pour avoir un timestamp différent
    backup2 = writer.backup_note(sample_note_with_frontmatter)

    # Les deux backups doivent exister
    assert backup1.exists()
    assert backup2.exists()

    # Ils doivent être dans des snapshots différents
    assert backup1.parent != backup2.parent


# ─────────────────────────────────────────────────────────────────
# Tests de modification frontmatter
# ─────────────────────────────────────────────────────────────────

def test_update_frontmatter_adds_ai_metadata(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que update_frontmatter ajoute les métadonnées AI."""
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.85,
        backup=True
    )

    # Re-parser la note pour vérifier les changements
    frontmatter, content, _ = writer.parse_note_file(sample_note_with_frontmatter)

    # Vérifier les tags AI ajoutés
    assert "tags" in frontmatter
    tags = frontmatter["tags"]
    assert "AI-Category-dev-web" in tags
    assert "AI-Category-python" in tags

    # Vérifier que les tags existants sont préservés
    assert "existing-tag" in tags
    assert "another-tag" in tags

    # Vérifier les métadonnées AI
    assert "ai_categories" in frontmatter
    assert frontmatter["ai_categories"] == ["Développement Web", "Python"]
    assert frontmatter["ai_confidence"] == 0.85
    assert "ai_processed_date" in frontmatter

    # Vérifier que le contenu markdown est intact
    assert "# Test Content" in content
    assert "[[linked-note]]" in content


def test_update_frontmatter_creates_frontmatter_if_missing(
    writer,
    sample_note_without_frontmatter,
    sample_categories
):
    """Test que update_frontmatter crée un frontmatter si absent."""
    writer.update_frontmatter(
        sample_note_without_frontmatter,
        sample_categories,
        confidence=0.75,
        backup=False  # Pas de backup pour ce test
    )

    # Re-parser la note
    frontmatter, content, _ = writer.parse_note_file(sample_note_without_frontmatter)

    # Le frontmatter a été créé
    assert len(frontmatter) > 0
    assert "tags" in frontmatter
    assert "ai_categories" in frontmatter
    assert frontmatter["ai_confidence"] == 0.75

    # Le contenu original est préservé
    assert "# Test Note Without Frontmatter" in content


def test_update_frontmatter_merges_tags_without_duplicates(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que le merge des tags évite les doublons."""
    # Ajouter deux fois les mêmes catégories
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.8,
        backup=False
    )

    frontmatter1, _, _ = writer.parse_note_file(sample_note_with_frontmatter)
    tags1 = frontmatter1["tags"]

    # Appliquer à nouveau
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.9,
        backup=False
    )

    frontmatter2, _, _ = writer.parse_note_file(sample_note_with_frontmatter)
    tags2 = frontmatter2["tags"]

    # Les tags ne doivent pas être dupliqués
    assert len(tags2) == len(set(tags2))  # Pas de doublons
    assert tags2.count("AI-Category-dev-web") == 1
    assert tags2.count("AI-Category-python") == 1


def test_update_frontmatter_handles_string_tags(writer, temp_dir, sample_categories):
    """Test le handling des tags au format string (au lieu de list)."""
    # Créer une note avec tags au format string
    content = """---
title: Test
tags: tag1, tag2, tag3
---

Content.
"""
    note_path = temp_dir / "note_string_tags.md"
    note_path.write_text(content, encoding="utf-8")

    writer.update_frontmatter(
        note_path,
        sample_categories,
        confidence=0.7,
        backup=False
    )

    frontmatter, _, _ = writer.parse_note_file(note_path)
    tags = frontmatter["tags"]

    # Les tags doivent être convertis en liste
    assert isinstance(tags, list)
    assert "tag1" in tags
    assert "AI-Category-dev-web" in tags


def test_update_frontmatter_with_backup_disabled(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que backup=False n'crée pas de backup."""
    # Compter les backups avant
    backup_count_before = len(list(writer.backup_dir.glob("*/*"))) if writer.backup_dir.exists() else 0

    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.8,
        backup=False  # Pas de backup
    )

    # Compter les backups après
    backup_count_after = len(list(writer.backup_dir.glob("*/*"))) if writer.backup_dir.exists() else 0

    # Aucun nouveau backup créé
    assert backup_count_after == backup_count_before


# ─────────────────────────────────────────────────────────────────
# Tests de apply_categories_to_note
# ─────────────────────────────────────────────────────────────────

def test_apply_categories_to_note(writer, sample_note_with_frontmatter, sample_categories):
    """Test apply_categories_to_note (wrapper de update_frontmatter)."""
    # Créer un objet Note
    note = Note(
        id="note1",
        file_path=str(sample_note_with_frontmatter),
        file_name=sample_note_with_frontmatter.name,
        relative_path=str(sample_note_with_frontmatter.relative_to(sample_note_with_frontmatter.parent.parent)),
        title="Test Note",
        content="Test content"
    )

    writer.apply_categories_to_note(
        note,
        sample_categories,
        confidence=0.88,
        backup=True
    )

    # Vérifier que les catégories sont appliquées
    frontmatter, _, _ = writer.parse_note_file(sample_note_with_frontmatter)

    assert "ai_categories" in frontmatter
    assert frontmatter["ai_confidence"] == 0.88
    assert "AI-Category-dev-web" in frontmatter["tags"]


# ─────────────────────────────────────────────────────────────────
# Tests de suppression métadonnées AI
# ─────────────────────────────────────────────────────────────────

def test_remove_ai_metadata_cleans_tags_and_fields(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que remove_ai_metadata supprime tous les champs AI."""
    # D'abord, ajouter des métadonnées AI
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.9,
        backup=False
    )

    # Vérifier qu'elles sont présentes
    frontmatter1, _, _ = writer.parse_note_file(sample_note_with_frontmatter)
    assert "ai_categories" in frontmatter1
    assert "AI-Category-dev-web" in frontmatter1["tags"]

    # Supprimer les métadonnées AI
    writer.remove_ai_metadata(sample_note_with_frontmatter, backup=False)

    # Vérifier qu'elles sont supprimées
    frontmatter2, _, _ = writer.parse_note_file(sample_note_with_frontmatter)

    # Champs AI supprimés
    assert "ai_categories" not in frontmatter2
    assert "ai_confidence" not in frontmatter2
    assert "ai_processed_date" not in frontmatter2

    # Tags AI supprimés
    assert "AI-Category-dev-web" not in frontmatter2["tags"]
    assert "AI-Category-python" not in frontmatter2["tags"]

    # Tags originaux préservés
    assert "existing-tag" in frontmatter2["tags"]
    assert "another-tag" in frontmatter2["tags"]


def test_remove_ai_metadata_handles_note_without_ai_metadata(
    writer,
    sample_note_with_frontmatter
):
    """Test remove_ai_metadata sur une note sans métadonnées AI."""
    # La note n'a pas de métadonnées AI au départ
    # remove_ai_metadata ne doit pas planter
    writer.remove_ai_metadata(sample_note_with_frontmatter, backup=False)

    # Vérifier que la note est intacte
    frontmatter, content, _ = writer.parse_note_file(sample_note_with_frontmatter)

    assert frontmatter["title"] == "Test Note"
    assert "existing-tag" in frontmatter["tags"]
    assert "# Test Content" in content


def test_remove_ai_metadata_with_backup(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que remove_ai_metadata crée un backup si demandé."""
    # Ajouter métadonnées AI
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.9,
        backup=False
    )

    # Compter les backups avant
    backup_count_before = len(list(writer.backup_dir.glob("*/*"))) if writer.backup_dir.exists() else 0

    # Supprimer avec backup
    writer.remove_ai_metadata(sample_note_with_frontmatter, backup=True)

    # Compter les backups après
    backup_count_after = len(list(writer.backup_dir.glob("*/*")))

    # Un nouveau backup créé
    assert backup_count_after == backup_count_before + 1


# ─────────────────────────────────────────────────────────────────
# Tests de préservation structure YAML
# ─────────────────────────────────────────────────────────────────

def test_preserve_yaml_structure(writer, temp_dir, sample_categories):
    """Test que la structure YAML est préservée (ordre, style)."""
    # Créer une note avec structure YAML spécifique
    content = """---
title: Preserved Note
author: Jobierre
date: 2026-01-11
tags:
  - first-tag
  - second-tag
metadata:
  complexity: high
  priority: 1
---

Content here.
"""
    note_path = temp_dir / "note_preserved.md"
    note_path.write_text(content, encoding="utf-8")

    # Modifier le frontmatter
    writer.update_frontmatter(
        note_path,
        sample_categories,
        confidence=0.85,
        backup=False
    )

    # Re-lire le fichier
    frontmatter, _, _ = writer.parse_note_file(note_path)

    # Vérifier que les champs originaux sont préservés
    assert frontmatter["title"] == "Preserved Note"
    assert frontmatter["author"] == "Jobierre"
    assert "metadata" in frontmatter
    assert frontmatter["metadata"]["complexity"] == "high"

    # Vérifier que les nouveaux champs AI sont ajoutés
    assert "ai_categories" in frontmatter
    assert "AI-Category-dev-web" in frontmatter["tags"]


# ─────────────────────────────────────────────────────────────────
# Tests edge cases
# ─────────────────────────────────────────────────────────────────

def test_update_frontmatter_with_empty_categories(
    writer,
    sample_note_with_frontmatter
):
    """Test update_frontmatter avec liste vide de catégories."""
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        categories=[],  # Liste vide
        confidence=0.0,
        backup=False
    )

    frontmatter, _, _ = writer.parse_note_file(sample_note_with_frontmatter)

    # Métadonnées AI présentes mais vides
    assert frontmatter["ai_categories"] == []
    assert frontmatter["ai_confidence"] == 0.0


def test_create_frontmatter_if_missing(writer):
    """Test la création d'un frontmatter vide."""
    frontmatter = writer.create_frontmatter_if_missing()

    assert len(frontmatter) == 0
    assert isinstance(frontmatter, dict)


# ─────────────────────────────────────────────────────────────────
# Tests de robustesse
# ─────────────────────────────────────────────────────────────────

def test_update_frontmatter_preserves_content(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que le contenu markdown reste intact après modification."""
    # Lire le contenu original
    _, original_content, _ = writer.parse_note_file(sample_note_with_frontmatter)

    # Modifier le frontmatter
    writer.update_frontmatter(
        sample_note_with_frontmatter,
        sample_categories,
        confidence=0.9,
        backup=False
    )

    # Re-lire le contenu
    _, modified_content, _ = writer.parse_note_file(sample_note_with_frontmatter)

    # Le contenu doit être identique
    assert original_content == modified_content
    assert "# Test Content" in modified_content
    assert "[[linked-note]]" in modified_content


def test_concurrent_modifications_dont_corrupt_file(
    writer,
    sample_note_with_frontmatter,
    sample_categories
):
    """Test que plusieurs modifications successives ne corrompent pas le fichier."""
    # Appliquer 5 modifications successives
    for i in range(5):
        confidence = 0.5 + (i * 0.1)
        writer.update_frontmatter(
            sample_note_with_frontmatter,
            sample_categories,
            confidence=confidence,
            backup=False
        )

    # Le fichier doit toujours être valide
    frontmatter, content, _ = writer.parse_note_file(sample_note_with_frontmatter)

    # Vérifier que le frontmatter est valide
    assert "ai_confidence" in frontmatter
    assert frontmatter["ai_confidence"] == 0.9  # Dernière valeur

    # Vérifier que le contenu est intact
    assert "# Test Content" in content
