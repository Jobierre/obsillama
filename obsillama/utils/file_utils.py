"""
ObsIllama - File Utilities

Ce module fournit des utilitaires pour la gestion des fichiers et des backups.
BackupManager permet de créer des snapshots, restaurer et gérer les backups.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configuration du logger
logger = logging.getLogger(__name__)


class BackupManager:
    """
    Gestionnaire centralisé de backups avec snapshots.

    Features:
    - Création de snapshots avec timestamp
    - Métadonnées JSON pour tracking
    - Restauration de snapshots complets ou fichiers individuels
    - Listing et statistiques des backups
    - Nettoyage automatique des anciens backups
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Initialise le BackupManager.

        Args:
            backup_dir: Dossier racine des backups (défaut: .obsillama_backups/)
        """
        self.backup_dir = backup_dir or Path(".obsillama_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"BackupManager initialisé avec backup_dir={self.backup_dir}")

    def create_backup_snapshot(self, description: str = "") -> str:
        """
        Crée un nouveau snapshot de backup avec timestamp unique.

        Un snapshot est un dossier qui contient:
        - Les fichiers backupés
        - Un fichier snapshot_metadata.json avec les infos

        Args:
            description: Description optionnelle du snapshot

        Returns:
            str: ID du snapshot (timestamp au format YYYYMMDD_HHMMSS)

        Examples:
            >>> manager = BackupManager()
            >>> snapshot_id = manager.create_backup_snapshot("Before apply")
            >>> snapshot_id
            '20260111_171430'
        """
        # Générer un ID unique avec timestamp
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.backup_dir / snapshot_id

        # Créer le dossier du snapshot
        snapshot_path.mkdir(parents=True, exist_ok=True)

        # Créer les métadonnées
        metadata = {
            "snapshot_id": snapshot_id,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "file_count": 0,
            "files": []
        }

        # Sauvegarder les métadonnées
        metadata_path = snapshot_path / "snapshot_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Snapshot créé: {snapshot_id}")
        return snapshot_id

    def backup_file(
        self,
        file_path: Path,
        snapshot_id: str,
        preserve_structure: bool = True,
        vault_root: Optional[Path] = None
    ) -> Path:
        """
        Backup un fichier dans un snapshot existant.

        Args:
            file_path: Chemin du fichier à backuper
            snapshot_id: ID du snapshot cible
            preserve_structure: Si True, préserve la structure de dossiers
            vault_root: Racine du vault (pour structure relative)

        Returns:
            Path: Chemin du fichier de backup créé

        Raises:
            FileNotFoundError: Si le fichier ou snapshot n'existe pas
            IOError: Si la copie échoue

        Examples:
            >>> manager = BackupManager()
            >>> snapshot_id = manager.create_backup_snapshot()
            >>> backup_path = manager.backup_file(Path("notes/test.md"), snapshot_id)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")

        snapshot_path = self.backup_dir / snapshot_id

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot non trouvé: {snapshot_id}")

        # Déterminer le chemin de destination
        if preserve_structure and vault_root and vault_root in file_path.parents:
            # Préserver la structure relative au vault
            relative_path = file_path.relative_to(vault_root)
            backup_path = snapshot_path / relative_path
        else:
            # Backup simple (juste le nom du fichier)
            backup_path = snapshot_path / file_path.name

        # Créer les dossiers parents si nécessaire
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copier le fichier
        try:
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Fichier backupé: {file_path} → {backup_path}")
        except Exception as e:
            logger.error(f"Erreur lors du backup de {file_path}: {e}")
            raise IOError(f"Échec backup: {e}")

        # Mettre à jour les métadonnées
        self._update_snapshot_metadata(
            snapshot_id,
            file_path,
            backup_path
        )

        return backup_path

    def restore_backup(
        self,
        snapshot_id: str,
        target_dir: Optional[Path] = None,
        file_name: Optional[str] = None
    ) -> List[Path]:
        """
        Restaure un snapshot complet ou un fichier spécifique.

        Args:
            snapshot_id: ID du snapshot à restaurer
            target_dir: Dossier de destination (défaut: emplacement original)
            file_name: Nom du fichier à restaurer (None = tout le snapshot)

        Returns:
            List[Path]: Liste des fichiers restaurés

        Raises:
            FileNotFoundError: Si le snapshot n'existe pas

        Examples:
            >>> manager = BackupManager()
            >>> restored = manager.restore_backup("20260111_171430")
            >>> len(restored)
            5
        """
        snapshot_path = self.backup_dir / snapshot_id

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot non trouvé: {snapshot_id}")

        # Charger les métadonnées
        metadata = self._load_snapshot_metadata(snapshot_id)
        restored_files = []

        # Restaurer un fichier spécifique ou tous
        files_to_restore = metadata.get("files", [])

        if file_name:
            files_to_restore = [f for f in files_to_restore if Path(f["backup_path"]).name == file_name]

        for file_info in files_to_restore:
            backup_path = snapshot_path / file_info["backup_path"]
            original_path = Path(file_info["original_path"])

            # Déterminer la destination
            if target_dir:
                restore_path = target_dir / backup_path.name
            else:
                restore_path = original_path

            # Créer les dossiers parents
            restore_path.parent.mkdir(parents=True, exist_ok=True)

            # Copier le fichier
            try:
                shutil.copy2(backup_path, restore_path)
                restored_files.append(restore_path)
                logger.info(f"Fichier restauré: {backup_path} → {restore_path}")
            except Exception as e:
                logger.error(f"Erreur lors de la restauration de {backup_path}: {e}")

        logger.info(f"Snapshot {snapshot_id} restauré: {len(restored_files)} fichiers")
        return restored_files

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Liste tous les snapshots de backup avec leurs métadonnées.

        Returns:
            List[Dict]: Liste des snapshots avec infos
                [
                    {
                        "snapshot_id": "20260111_171430",
                        "description": "...",
                        "created_at": "...",
                        "file_count": 5
                    },
                    ...
                ]

        Examples:
            >>> manager = BackupManager()
            >>> backups = manager.list_backups()
            >>> backups[0]["snapshot_id"]
            '20260111_171430'
        """
        backups = []

        # Parcourir tous les dossiers de snapshots
        for snapshot_dir in sorted(self.backup_dir.iterdir()):
            if not snapshot_dir.is_dir():
                continue

            snapshot_id = snapshot_dir.name

            # Charger les métadonnées si disponibles
            try:
                metadata = self._load_snapshot_metadata(snapshot_id)
                backups.append({
                    "snapshot_id": metadata.get("snapshot_id", snapshot_id),
                    "description": metadata.get("description", ""),
                    "created_at": metadata.get("created_at", ""),
                    "file_count": metadata.get("file_count", 0)
                })
            except Exception as e:
                # Si pas de métadonnées, créer une entrée basique
                logger.debug(f"Métadonnées manquantes pour {snapshot_id}: {e}")
                backups.append({
                    "snapshot_id": snapshot_id,
                    "description": "(métadonnées manquantes)",
                    "created_at": datetime.fromtimestamp(
                        snapshot_dir.stat().st_mtime
                    ).isoformat(),
                    "file_count": len(list(snapshot_dir.glob("*.md")))
                })

        return backups

    def cleanup_old_backups(self, keep_last: int = 10) -> int:
        """
        Supprime les anciens snapshots en gardant les N plus récents.

        Args:
            keep_last: Nombre de snapshots à garder (défaut: 10)

        Returns:
            int: Nombre de snapshots supprimés

        Examples:
            >>> manager = BackupManager()
            >>> deleted = manager.cleanup_old_backups(keep_last=5)
            >>> deleted
            3
        """
        backups = self.list_backups()

        # Trier par date (du plus récent au plus ancien)
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        # Snapshots à supprimer (tous sauf les keep_last premiers)
        to_delete = backups[keep_last:]

        deleted_count = 0

        for backup_info in to_delete:
            snapshot_id = backup_info["snapshot_id"]
            snapshot_path = self.backup_dir / snapshot_id

            try:
                shutil.rmtree(snapshot_path)
                logger.info(f"Snapshot supprimé: {snapshot_id}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {snapshot_id}: {e}")

        logger.info(f"Cleanup terminé: {deleted_count} snapshots supprimés")
        return deleted_count

    def get_snapshot_info(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Récupère les informations détaillées d'un snapshot.

        Args:
            snapshot_id: ID du snapshot

        Returns:
            Dict: Métadonnées complètes du snapshot

        Raises:
            FileNotFoundError: Si le snapshot n'existe pas
        """
        return self._load_snapshot_metadata(snapshot_id)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Supprime un snapshot spécifique.

        Args:
            snapshot_id: ID du snapshot à supprimer

        Returns:
            bool: True si supprimé avec succès

        Raises:
            FileNotFoundError: Si le snapshot n'existe pas
        """
        snapshot_path = self.backup_dir / snapshot_id

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot non trouvé: {snapshot_id}")

        try:
            shutil.rmtree(snapshot_path)
            logger.info(f"Snapshot supprimé: {snapshot_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de {snapshot_id}: {e}")
            return False

    def get_total_backup_size(self) -> int:
        """
        Calcule la taille totale de tous les backups.

        Returns:
            int: Taille totale en bytes

        Examples:
            >>> manager = BackupManager()
            >>> size = manager.get_total_backup_size()
            >>> size
            15728640  # ~15MB
        """
        total_size = 0

        for snapshot_dir in self.backup_dir.iterdir():
            if snapshot_dir.is_dir():
                for file in snapshot_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size

        return total_size

    def format_size(self, size_bytes: int) -> str:
        """
        Formate une taille en bytes en format lisible.

        Args:
            size_bytes: Taille en bytes

        Returns:
            str: Taille formatée (ex: "15.2 MB")

        Examples:
            >>> manager = BackupManager()
            >>> manager.format_size(15728640)
            '15.0 MB'
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0

        return f"{size_bytes:.1f} PB"

    # ========================================================================
    # Méthodes privées
    # ========================================================================

    def _load_snapshot_metadata(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Charge les métadonnées d'un snapshot.

        Args:
            snapshot_id: ID du snapshot

        Returns:
            Dict: Métadonnées du snapshot

        Raises:
            FileNotFoundError: Si les métadonnées n'existent pas
        """
        metadata_path = self.backup_dir / snapshot_id / "snapshot_metadata.json"

        if not metadata_path.exists():
            raise FileNotFoundError(f"Métadonnées non trouvées: {metadata_path}")

        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _update_snapshot_metadata(
        self,
        snapshot_id: str,
        original_path: Path,
        backup_path: Path
    ) -> None:
        """
        Met à jour les métadonnées d'un snapshot après l'ajout d'un fichier.

        Args:
            snapshot_id: ID du snapshot
            original_path: Chemin original du fichier
            backup_path: Chemin du backup
        """
        try:
            metadata = self._load_snapshot_metadata(snapshot_id)

            # Ajouter le fichier à la liste
            file_info = {
                "original_path": str(original_path),
                "backup_path": str(backup_path.relative_to(self.backup_dir / snapshot_id)),
                "timestamp": datetime.now().isoformat(),
                "size": original_path.stat().st_size
            }

            metadata["files"].append(file_info)
            metadata["file_count"] = len(metadata["files"])

            # Sauvegarder
            metadata_path = self.backup_dir / snapshot_id / "snapshot_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métadonnées: {e}")
