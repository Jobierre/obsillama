"""
Tests pour le scanner de notes et le parser de frontmatter

Ces tests vérifient:
- Parsing du frontmatter YAML
- Extraction des métadonnées
- Scanner de vault
- Échantillonnage
- Cache JSON
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from obsillama.core.frontmatter_parser import (
    parse_frontmatter,
    extract_tags_from_frontmatter,
    extract_inline_tags,
    extract_backlinks,
    extract_external_links,
    extract_title,
    count_words,
    count_headings,
    is_daily_note,
    parse_note_content,
)
from obsillama.core.note_scanner import NoteScanner
from obsillama.models.note import Note


# ============================================================================
# Fixtures pour les tests
# ============================================================================


@pytest.fixture
def temp_vault(tmp_path):
    """Crée un vault temporaire avec des notes de test."""
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # Note avec frontmatter complet
    note1 = vault / "Note 1.md"
    note1.write_text(
        """---
title: Test Note 1
tags: [tech, python]
author: Jobierre
---

# Introduction

Ceci est une note de test avec [[Note 2|lien]] et #inline-tag.

Voir https://example.com pour plus d'infos.

## Section 2

Du contenu avec plusieurs mots pour tester le word count.
"""
    )

    # Note sans frontmatter
    note2 = vault / "Note 2.md"
    note2.write_text(
        """# Note 2

Contenu simple sans frontmatter mais avec [[Note 1]].

#test #python
"""
    )

    # Daily note
    note3 = vault / "2026-01-09.md"
    note3.write_text(
        """---
tags: [daily-note]
---

# Daily Note

Événements du jour.
"""
    )

    # Note dans un sous-dossier
    subfolder = vault / "Projects"
    subfolder.mkdir()

    note4 = subfolder / "Project Note.md"
    note4.write_text(
        """---
title: Project Note
---

# Project

Note dans un sous-dossier.
"""
    )

    # Dossier à exclure
    excluded = vault / ".obsidian"
    excluded.mkdir()

    note_excluded = excluded / "excluded.md"
    note_excluded.write_text("Cette note doit être exclue")

    return vault


# ============================================================================
# Tests du frontmatter_parser
# ============================================================================


def test_parse_frontmatter_with_yaml():
    """Test parsing d'un frontmatter YAML valide."""
    content = """---
title: Test
tags: [tag1, tag2]
---

Contenu de la note
"""

    metadata, clean_content = parse_frontmatter(content)

    assert metadata["title"] == "Test"
    assert metadata["tags"] == ["tag1", "tag2"]
    assert clean_content == "Contenu de la note"


def test_parse_frontmatter_without_yaml():
    """Test parsing d'une note sans frontmatter."""
    content = "# Note sans frontmatter\n\nContenu"

    metadata, clean_content = parse_frontmatter(content)

    assert metadata == {}
    assert clean_content == content


def test_parse_frontmatter_empty():
    """Test parsing d'un contenu vide."""
    metadata, clean_content = parse_frontmatter("")

    assert metadata == {}
    assert clean_content == ""


def test_extract_tags_from_frontmatter_list():
    """Test extraction de tags (format liste)."""
    frontmatter = {"tags": ["tech", "python", "ai"]}

    tags = extract_tags_from_frontmatter(frontmatter)

    assert set(tags) == {"tech", "python", "ai"}


def test_extract_tags_from_frontmatter_string():
    """Test extraction de tags (format string)."""
    frontmatter = {"tags": "tech, python, ai"}

    tags = extract_tags_from_frontmatter(frontmatter)

    assert set(tags) == {"tech", "python", "ai"}


def test_extract_tags_from_frontmatter_single():
    """Test extraction d'un seul tag."""
    frontmatter = {"tag": "single-tag"}

    tags = extract_tags_from_frontmatter(frontmatter)

    assert tags == ["single-tag"]


def test_extract_inline_tags():
    """Test extraction de tags inline (#tag)."""
    content = "Ceci est un #test avec #python et #ai"

    tags = extract_inline_tags(content)

    assert set(tags) == {"test", "python", "ai"}


def test_extract_inline_tags_ignore_headings():
    """Test que les headings ne sont pas détectés comme tags."""
    content = """# Titre de niveau 1

Contenu avec #tag

## Sous-titre

Plus de #contenu
"""

    tags = extract_inline_tags(content)

    assert set(tags) == {"tag", "contenu"}


def test_extract_backlinks():
    """Test extraction de backlinks [[note]]."""
    content = "Voir [[Note 1]] et [[Note 2|avec alias]] pour plus d'infos"

    backlinks = extract_backlinks(content)

    assert set(backlinks) == {"Note 1", "Note 2"}


def test_extract_external_links():
    """Test extraction de liens externes."""
    content = "Voir https://example.com et http://test.org"

    links = extract_external_links(content)

    assert "https://example.com" in links
    assert "http://test.org" in links


def test_extract_title_from_frontmatter():
    """Test extraction du titre depuis le frontmatter."""
    frontmatter = {"title": "Titre du frontmatter"}
    content = "# Titre H1"

    title = extract_title(frontmatter, content, "fallback")

    assert title == "Titre du frontmatter"


def test_extract_title_from_h1():
    """Test extraction du titre depuis le H1."""
    frontmatter = {}
    content = "# Titre H1\n\nContenu"

    title = extract_title(frontmatter, content, "fallback")

    assert title == "Titre H1"


def test_extract_title_fallback():
    """Test fallback sur le nom du fichier."""
    frontmatter = {}
    content = "Pas de titre ici"

    title = extract_title(frontmatter, content, "fallback-filename")

    assert title == "fallback-filename"


def test_count_words():
    """Test comptage des mots."""
    content = "Ceci est un test avec plusieurs mots"

    assert count_words(content) == 7


def test_count_headings():
    """Test comptage des headings."""
    content = """# H1

## H2

### H3

Contenu

## H2 bis
"""

    assert count_headings(content) == 4


def test_is_daily_note_by_filename():
    """Test détection de daily note par le nom."""
    assert is_daily_note("2026-01-09", {}) is True
    assert is_daily_note("09-01-2026", {}) is True
    assert is_daily_note("20260109", {}) is True
    assert is_daily_note("Regular Note", {}) is False


def test_is_daily_note_by_tag():
    """Test détection de daily note par tag."""
    assert is_daily_note("Note", {"tags": ["daily-note"]}) is True
    assert is_daily_note("Note", {"tags": ["journal"]}) is True
    assert is_daily_note("Note", {"tags": ["other"]}) is False


def test_parse_note_content_complete():
    """Test parsing complet d'une note."""
    content = """---
title: Test Complete
tags: [tech, python]
---

# Introduction

Contenu avec [[lien]] et #inline-tag.

Plus de contenu ici.
"""

    result = parse_note_content(content, "test-file")

    assert result["title"] == "Test Complete"
    assert "tech" in result["frontmatter_tags"]
    assert "inline-tag" in result["inline_tags"]
    assert "lien" in result["backlinks"]
    assert result["word_count"] > 0
    assert result["heading_count"] == 1


# ============================================================================
# Tests du NoteScanner
# ============================================================================


def test_note_scanner_initialization(temp_vault):
    """Test initialisation du scanner."""
    scanner = NoteScanner(vault_path=str(temp_vault))

    assert scanner.vault_path == temp_vault
    assert scanner.cache_path.exists() or scanner.cache_path.parent.exists()


def test_scan_vault(temp_vault):
    """Test scan du vault."""
    scanner = NoteScanner(
        vault_path=str(temp_vault), exclude_folders=[".obsidian"]
    )

    files = scanner.scan_vault()

    # Doit trouver 4 notes (exclure .obsidian)
    assert len(files) == 4

    # Vérifier que les notes sont des Path
    assert all(isinstance(f, Path) for f in files)

    # Vérifier que les notes exclues ne sont pas là
    assert not any(".obsidian" in str(f) for f in files)


def test_parse_note(temp_vault):
    """Test parsing d'une note."""
    scanner = NoteScanner(vault_path=str(temp_vault))

    note_file = temp_vault / "Note 1.md"
    note = scanner.parse_note(note_file)

    assert isinstance(note, Note)
    assert note.title == "Test Note 1"
    assert "tech" in note.tags
    assert "python" in note.tags
    assert "inline-tag" in note.inline_tags
    assert "Note 2" in note.backlinks
    assert "https://example.com" in note.external_links
    assert note.word_count > 0


def test_parse_note_without_frontmatter(temp_vault):
    """Test parsing d'une note sans frontmatter."""
    scanner = NoteScanner(vault_path=str(temp_vault))

    note_file = temp_vault / "Note 2.md"
    note = scanner.parse_note(note_file)

    assert isinstance(note, Note)
    assert note.title == "Note 2"  # Depuis le H1
    assert "test" in note.tags
    assert "Note 1" in note.backlinks


def test_parse_note_daily(temp_vault):
    """Test parsing d'une daily note."""
    scanner = NoteScanner(vault_path=str(temp_vault))

    note_file = temp_vault / "2026-01-09.md"
    note = scanner.parse_note(note_file)

    assert note.is_daily_note is True


def test_parse_note_in_subfolder(temp_vault):
    """Test parsing d'une note dans un sous-dossier."""
    scanner = NoteScanner(vault_path=str(temp_vault))

    note_file = temp_vault / "Projects" / "Project Note.md"
    note = scanner.parse_note(note_file)

    assert note.folder == "Projects"


def test_scan_and_parse_all(temp_vault):
    """Test scan_and_parse avec stratégie 'all'."""
    scanner = NoteScanner(
        vault_path=str(temp_vault), exclude_folders=[".obsidian"]
    )

    notes = scanner.scan_and_parse(strategy="all")

    assert len(notes) == 4
    assert all(isinstance(n, Note) for n in notes)


def test_scan_and_parse_random(temp_vault):
    """Test scan_and_parse avec échantillonnage aléatoire."""
    scanner = NoteScanner(
        vault_path=str(temp_vault), exclude_folders=[".obsidian"]
    )

    notes = scanner.scan_and_parse(strategy="random", sample_size=2)

    assert len(notes) == 2


def test_scan_and_parse_stratified(temp_vault):
    """Test scan_and_parse avec échantillonnage stratifié."""
    scanner = NoteScanner(
        vault_path=str(temp_vault), exclude_folders=[".obsidian"]
    )

    notes = scanner.scan_and_parse(strategy="stratified", sample_percentage=50)

    assert len(notes) >= 1  # Au moins 1 note
    assert len(notes) <= 4  # Max 4 notes


def test_save_and_load_cache(temp_vault, tmp_path):
    """Test sauvegarde et chargement du cache."""
    cache_path = tmp_path / "test_cache.json"

    scanner = NoteScanner(
        vault_path=str(temp_vault),
        exclude_folders=[".obsidian"],
        cache_path=str(cache_path),
    )

    # Scanner et sauvegarder
    notes = scanner.scan_and_parse(strategy="all")
    scanner.save_cache(notes)

    # Vérifier que le cache existe
    assert cache_path.exists()

    # Charger le cache
    loaded_notes = scanner.load_cache()

    assert loaded_notes is not None
    assert len(loaded_notes) == len(notes)
    assert all(isinstance(n, Note) for n in loaded_notes)


def test_detect_new_notes(temp_vault, tmp_path):
    """Test détection de nouvelles notes."""
    cache_path = tmp_path / "test_cache.json"

    scanner = NoteScanner(
        vault_path=str(temp_vault),
        exclude_folders=[".obsidian"],
        cache_path=str(cache_path),
    )

    # Scanner et cacher 2 notes
    notes = scanner.scan_and_parse(strategy="random", sample_size=2)
    scanner.save_cache(notes)

    # Ajouter une nouvelle note
    new_note = temp_vault / "New Note.md"
    new_note.write_text("# New Note\n\nContenu")

    # Détecter les nouvelles notes
    loaded_notes = scanner.load_cache()
    new_files = scanner.detect_new_notes(loaded_notes)

    # Doit trouver au moins la nouvelle note
    assert len(new_files) >= 1
    assert any("New Note.md" in str(f) for f in new_files)


def test_generate_note_id(temp_vault):
    """Test génération d'ID unique."""
    scanner = NoteScanner(vault_path=str(temp_vault))

    id1 = scanner._generate_note_id("path/to/note1.md")
    id2 = scanner._generate_note_id("path/to/note2.md")
    id3 = scanner._generate_note_id("path/to/note1.md")  # Même chemin

    assert id1 != id2  # IDs différents pour chemins différents
    assert id1 == id3  # Même ID pour même chemin
    assert len(id1) == 16  # Tronqué à 16 caractères


# ============================================================================
# Tests d'intégration
# ============================================================================


@pytest.mark.integration
def test_real_vault_scan():
    """
    Test sur le vault réel.

    Note: Ce test nécessite que le vault existe.
    """
    vault_path = "/Users/jordanmirmand/Documents/Obsidian and CO/obsinote"

    if not Path(vault_path).exists():
        pytest.skip("Vault réel non accessible")

    scanner = NoteScanner(vault_path=vault_path)

    # Scanner 10 notes au hasard
    notes = scanner.scan_and_parse(strategy="random", sample_size=10)

    assert len(notes) <= 10
    assert all(isinstance(n, Note) for n in notes)

    # Afficher quelques stats
    for note in notes[:3]:
        print(f"\nNote: {note.title}")
        print(f"  Words: {note.word_count}")
        print(f"  Tags: {note.tags[:5]}")
        print(f"  Backlinks: {len(note.backlinks)}")
