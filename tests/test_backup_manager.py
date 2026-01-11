"""
Tests pour BackupManager - Phase 5.2

Test du BackupManager avec pytest:
- Création de snapshots
- Backup de fichiers
- Métadonnées de snapshots
- Listing des backups
- Restauration de fichiers
- Cleanup automatique
- Suppression de snapshots
- Calcul de taille
"""

import pytest
import time
from pathlib import Path
from datetime import datetime

from obsillama.utils.file_utils import BackupManager


@pytest.fixture
def backup_dir(tmp_path):
    """Crée un répertoire de backup temporaire."""
    backup = tmp_path / "test_backups"
    backup.mkdir()
    return backup


@pytest.fixture
def vault_dir(tmp_path):
    """Crée un répertoire vault temporaire avec des notes."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Créer quelques notes de test
    for i in range(3):
        note_path = vault / f"note_{i}.md"
        note_path.write_text(f"# Note {i}\n\nContenu de la note {i}", encoding="utf-8")

    return vault


@pytest.fixture
def manager(backup_dir):
    """Crée une instance de BackupManager."""
    return BackupManager(backup_dir=backup_dir)


class TestBackupManagerSnapshots:
    """Tests de création de snapshots."""

    def test_create_backup_snapshot(self, manager, backup_dir):
        """Test: Créer un snapshot génère un ID avec timestamp."""
        snapshot_id = manager.create_backup_snapshot(description="Test backup initial")

        assert snapshot_id is not None
        assert len(snapshot_id) == 15  # Format YYYYMMDD_HHMMSS

        # Vérifier que le dossier existe
        snapshot_path = backup_dir / snapshot_id
        assert snapshot_path.exists()
        assert snapshot_path.is_dir()

        # Vérifier que les métadonnées existent
        metadata_path = snapshot_path / "snapshot_metadata.json"
        assert metadata_path.exists()

    def test_snapshot_metadata_structure(self, manager):
        """Test: Les métadonnées du snapshot ont la bonne structure."""
        snapshot_id = manager.create_backup_snapshot(description="Test metadata")

        metadata = manager.get_snapshot_info(snapshot_id)

        assert "snapshot_id" in metadata
        assert "description" in metadata
        assert "created_at" in metadata
        assert "file_count" in metadata
        assert "files" in metadata

        assert metadata["snapshot_id"] == snapshot_id
        assert metadata["description"] == "Test metadata"
        assert metadata["file_count"] == 0
        assert isinstance(metadata["files"], list)


class TestBackupManagerFiles:
    """Tests de backup de fichiers."""

    def test_backup_file_simple(self, manager, vault_dir):
        """Test: Backup un fichier dans un snapshot."""
        snapshot_id = manager.create_backup_snapshot()
        note_path = vault_dir / "note_0.md"

        backup_path = manager.backup_file(note_path, snapshot_id, preserve_structure=False)

        assert backup_path.exists()
        assert backup_path.name == "note_0.md"

        # Vérifier que le contenu est identique
        original_content = note_path.read_text(encoding="utf-8")
        backup_content = backup_path.read_text(encoding="utf-8")
        assert original_content == backup_content

    def test_backup_multiple_files(self, manager, vault_dir):
        """Test: Backup plusieurs fichiers dans le même snapshot."""
        snapshot_id = manager.create_backup_snapshot()

        # Backup 3 fichiers
        for i in range(3):
            note_path = vault_dir / f"note_{i}.md"
            manager.backup_file(note_path, snapshot_id, preserve_structure=False)

        # Vérifier les métadonnées
        metadata = manager.get_snapshot_info(snapshot_id)
        assert metadata["file_count"] == 3
        assert len(metadata["files"]) == 3

    def test_backup_file_with_structure(self, manager, vault_dir):
        """Test: Backup avec préservation de la structure."""
        snapshot_id = manager.create_backup_snapshot()
        note_path = vault_dir / "note_0.md"

        backup_path = manager.backup_file(
            note_path,
            snapshot_id,
            preserve_structure=True,
            vault_root=vault_dir
        )

        # Le path devrait être relatif au vault
        assert backup_path.name == "note_0.md"

    def test_backup_nonexistent_file(self, manager):
        """Test: Erreur si le fichier n'existe pas."""
        snapshot_id = manager.create_backup_snapshot()

        with pytest.raises(FileNotFoundError):
            manager.backup_file(Path("nonexistent.md"), snapshot_id)


class TestBackupManagerListing:
    """Tests de listing des backups."""

    def test_list_backups_empty(self, manager):
        """Test: Liste vide si aucun backup."""
        backups = manager.list_backups()
        assert len(backups) == 0

    def test_list_backups_multiple(self, manager, vault_dir):
        """Test: Lister plusieurs snapshots."""
        # Créer 3 snapshots
        for i in range(3):
            snapshot_id = manager.create_backup_snapshot(description=f"Backup {i}")
            time.sleep(1)  # Pour avoir des timestamps différents (précision: seconde)

        backups = manager.list_backups()
        assert len(backups) == 3

        # Vérifier la structure
        for backup in backups:
            assert "snapshot_id" in backup
            assert "description" in backup
            assert "created_at" in backup
            assert "file_count" in backup


class TestBackupManagerRestore:
    """Tests de restauration."""

    def test_restore_backup_single_file(self, manager, vault_dir, tmp_path):
        """Test: Restaurer un fichier depuis un backup."""
        # Créer un backup
        snapshot_id = manager.create_backup_snapshot()
        note_path = vault_dir / "note_0.md"
        original_content = note_path.read_text(encoding="utf-8")

        manager.backup_file(note_path, snapshot_id, preserve_structure=False)

        # Modifier le fichier original
        note_path.write_text("# Contenu modifié\n\nCe fichier a été modifié!", encoding="utf-8")

        # Restaurer depuis le backup
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()

        restored = manager.restore_backup(
            snapshot_id,
            target_dir=restore_dir,
            file_name="note_0.md"
        )

        assert len(restored) == 1

        # Vérifier que le contenu restauré est l'original
        restored_content = restored[0].read_text(encoding="utf-8")
        assert restored_content == original_content

    def test_restore_full_snapshot(self, manager, vault_dir, tmp_path):
        """Test: Restaurer un snapshot complet."""
        # Créer un backup de 3 fichiers
        snapshot_id = manager.create_backup_snapshot()

        for i in range(3):
            note_path = vault_dir / f"note_{i}.md"
            manager.backup_file(note_path, snapshot_id, preserve_structure=False)

        # Restaurer tout le snapshot
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()

        restored = manager.restore_backup(snapshot_id, target_dir=restore_dir)

        assert len(restored) == 3

        # Vérifier que tous les fichiers sont restaurés
        for i in range(3):
            restored_file = restore_dir / f"note_{i}.md"
            assert restored_file.exists()


class TestBackupManagerCleanup:
    """Tests de nettoyage des backups."""

    def test_cleanup_old_backups(self, manager):
        """Test: Cleanup supprime les anciens backups."""
        # Créer 5 snapshots avec délai pour timestamps uniques
        for i in range(5):
            manager.create_backup_snapshot(description=f"Backup {i}")
            time.sleep(1)  # 1 seconde de délai

        # Vérifier qu'on a 5 backups
        backups_before = manager.list_backups()
        assert len(backups_before) == 5

        # Cleanup en gardant seulement les 2 derniers
        deleted = manager.cleanup_old_backups(keep_last=2)

        assert deleted == 3

        # Vérifier qu'il reste 2 backups
        backups_after = manager.list_backups()
        assert len(backups_after) == 2

    def test_cleanup_keeps_most_recent(self, manager):
        """Test: Cleanup garde les backups les plus récents."""
        # Créer 4 snapshots
        snapshot_ids = []
        for i in range(4):
            snapshot_id = manager.create_backup_snapshot(description=f"Backup {i}")
            snapshot_ids.append(snapshot_id)
            time.sleep(1)

        # Cleanup en gardant les 2 derniers
        manager.cleanup_old_backups(keep_last=2)

        # Les 2 plus récents devraient exister
        backups = manager.list_backups()
        remaining_ids = [b["snapshot_id"] for b in backups]

        assert snapshot_ids[-1] in remaining_ids  # Le plus récent
        assert snapshot_ids[-2] in remaining_ids  # Le 2ème plus récent
        assert snapshot_ids[0] not in remaining_ids  # Le plus ancien supprimé


class TestBackupManagerDeletion:
    """Tests de suppression de snapshots."""

    def test_delete_snapshot(self, manager):
        """Test: Supprimer un snapshot spécifique."""
        snapshot_id = manager.create_backup_snapshot()

        # Vérifier qu'il existe
        backups_before = manager.list_backups()
        assert len(backups_before) == 1

        # Supprimer
        result = manager.delete_snapshot(snapshot_id)
        assert result is True

        # Vérifier qu'il n'existe plus
        backups_after = manager.list_backups()
        assert len(backups_after) == 0

    def test_delete_nonexistent_snapshot(self, manager):
        """Test: Erreur si le snapshot n'existe pas."""
        with pytest.raises(FileNotFoundError):
            manager.delete_snapshot("nonexistent_20260111_000000")


class TestBackupManagerSize:
    """Tests de calcul de taille."""

    def test_get_total_backup_size(self, manager, vault_dir):
        """Test: Calculer la taille totale des backups."""
        snapshot_id = manager.create_backup_snapshot()

        # Backup 3 fichiers
        for i in range(3):
            note_path = vault_dir / f"note_{i}.md"
            manager.backup_file(note_path, snapshot_id, preserve_structure=False)

        # Calculer la taille
        total_size = manager.get_total_backup_size()

        assert total_size > 0

    def test_format_size(self, manager):
        """Test: Formater une taille en format lisible."""
        assert manager.format_size(500) == "500.0 B"
        assert manager.format_size(1500) == "1.5 KB"
        assert manager.format_size(1500000) == "1.4 MB"
        assert "GB" in manager.format_size(2000000000)
