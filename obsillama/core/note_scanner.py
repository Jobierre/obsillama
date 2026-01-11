"""
ObsIllama - Note Scanner

Ce module gère le scan du vault Obsidian et le parsing des notes.
Il supporte l'échantillonnage et le cache des notes parsées.
"""

import json
import hashlib
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any

from obsillama.config.settings import get_settings
from obsillama.models.note import Note
from obsillama.core.frontmatter_parser import parse_note_content

# Configuration du logger
logger = logging.getLogger(__name__)


# ============================================================================
# Classe NoteScanner
# ============================================================================


class NoteScanner:
    """
    Scanner de notes pour le vault Obsidian.

    Cette classe permet de:
    - Scanner le vault pour trouver tous les fichiers .md
    - Parser les notes avec extraction de métadonnées
    - Supporter l'échantillonnage (random, stratified, all)
    - Cacher les notes parsées pour améliorer les performances
    - Détecter les notes nouvelles/modifiées

    Attributes:
        vault_path: Chemin vers le vault Obsidian
        exclude_folders: Liste des dossiers à exclure
        cache_path: Chemin vers le fichier de cache JSON
    """

    def __init__(
        self,
        vault_path: Optional[str] = None,
        exclude_folders: Optional[List[str]] = None,
        cache_path: Optional[str] = None,
    ):
        """
        Initialise le scanner.

        Args:
            vault_path: Chemin vers le vault (défaut: depuis config)
            exclude_folders: Dossiers à exclure (défaut: depuis config)
            cache_path: Chemin du cache JSON (défaut: data/cache/scanned_notes.json)
        """
        # Charger la configuration
        settings = get_settings()

        self.vault_path = Path(vault_path or settings.vault.path)
        self.exclude_folders = exclude_folders or settings.vault.exclude_folders
        self.cache_path = Path(
            cache_path or "data/cache/scanned_notes.json"
        ).resolve()

        # Créer le dossier cache si nécessaire
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"NoteScanner initialisé - vault: {self.vault_path}, "
            f"exclusions: {self.exclude_folders}"
        )

    def scan_vault(self) -> List[Path]:
        """
        Scan le vault pour trouver tous les fichiers .md.

        Exclut les dossiers spécifiés dans la configuration.

        Returns:
            List[Path]: Liste des chemins vers les fichiers .md trouvés

        Raises:
            FileNotFoundError: Si le vault n'existe pas
        """
        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault introuvable: {self.vault_path}")

        logger.info(f"Scan du vault: {self.vault_path}")

        markdown_files = []

        # Scanner récursivement
        for md_file in self.vault_path.rglob("*.md"):
            # Vérifier si le fichier est dans un dossier exclu
            relative_path = md_file.relative_to(self.vault_path)

            if self._is_excluded(relative_path):
                logger.debug(f"Fichier exclu: {relative_path}")
                continue

            markdown_files.append(md_file)

        logger.info(f"Scan terminé: {len(markdown_files)} notes trouvées")

        return markdown_files

    def _is_excluded(self, relative_path: Path) -> bool:
        """
        Vérifie si un chemin doit être exclu.

        Args:
            relative_path: Chemin relatif depuis la racine du vault

        Returns:
            bool: True si le fichier doit être exclu
        """
        # Vérifier chaque partie du chemin
        for part in relative_path.parts:
            if part in self.exclude_folders:
                return True

        return False

    def parse_note(self, file_path: Path) -> Note:
        """
        Parse une note Obsidian et crée un objet Note.

        Args:
            file_path: Chemin vers le fichier .md

        Returns:
            Note: Objet Note validé avec toutes les métadonnées

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si la note ne peut pas être parsée
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {file_path}")

        logger.debug(f"Parsing de la note: {file_path}")

        try:
            # Lire le contenu
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            # Informations du fichier
            file_stat = file_path.stat()
            created_at = datetime.fromtimestamp(file_stat.st_ctime)
            modified_at = datetime.fromtimestamp(file_stat.st_mtime)

            # Chemins
            absolute_path = file_path.resolve()
            relative_path = file_path.relative_to(self.vault_path)
            filename = file_path.name
            filename_without_ext = file_path.stem

            # Dossier parent
            folder_parts = list(relative_path.parent.parts)
            folder = "/".join(folder_parts) if folder_parts else ""

            # Générer un ID unique (hash du chemin)
            note_id = self._generate_note_id(str(relative_path))

            # Parser le contenu
            parsed_data = parse_note_content(raw_content, filename_without_ext)

            # Créer l'objet Note
            note = Note(
                id=note_id,
                file_path=str(absolute_path),
                file_name=filename,
                relative_path=str(relative_path),
                created_at=created_at,
                modified_at=modified_at,
                folder=folder,
                **parsed_data,
            )

            logger.debug(
                f"Note parsée: {note.title} "
                f"({note.word_count} mots, {len(note.tags)} tags)"
            )

            return note

        except Exception as e:
            logger.error(f"Erreur lors du parsing de {file_path}: {e}")
            raise ValueError(f"Impossible de parser la note: {e}") from e

    def _generate_note_id(self, relative_path: str) -> str:
        """
        Génère un ID unique pour une note basé sur son chemin.

        Args:
            relative_path: Chemin relatif de la note

        Returns:
            str: ID unique (hash SHA256 tronqué)
        """
        hash_obj = hashlib.sha256(relative_path.encode())
        return hash_obj.hexdigest()[:16]

    def scan_and_parse(
        self,
        strategy: Literal["all", "random", "stratified"] = "all",
        sample_size: Optional[int] = None,
        sample_percentage: Optional[int] = None,
    ) -> List[Note]:
        """
        Scan le vault et parse les notes selon la stratégie d'échantillonnage.

        Stratégies d'échantillonnage:
        - "all": Parse toutes les notes
        - "random": Échantillonnage aléatoire simple
        - "stratified": Échantillonnage stratifié par dossier

        Args:
            strategy: Stratégie d'échantillonnage
            sample_size: Nombre de notes à échantillonner (prioritaire)
            sample_percentage: Pourcentage de notes à échantillonner (si sample_size None)

        Returns:
            List[Note]: Liste des notes parsées

        Examples:
            >>> scanner.scan_and_parse("all")  # Toutes les notes
            >>> scanner.scan_and_parse("random", sample_size=50)  # 50 notes au hasard
            >>> scanner.scan_and_parse("stratified", sample_percentage=15)  # 15% par dossier
        """
        # Scanner le vault
        all_files = self.scan_vault()

        if not all_files:
            logger.warning("Aucun fichier .md trouvé dans le vault")
            return []

        # Sélectionner les fichiers selon la stratégie
        if strategy == "all":
            selected_files = all_files
            logger.info("Stratégie: parse de toutes les notes")

        else:
            # Calculer la taille de l'échantillon
            if sample_size:
                target_size = min(sample_size, len(all_files))
            elif sample_percentage:
                target_size = max(1, int(len(all_files) * sample_percentage / 100))
            else:
                # Par défaut: 15% (depuis config)
                settings = get_settings()
                target_size = max(
                    1, int(len(all_files) * settings.processing.sampling.percentage / 100)
                )

            logger.info(
                f"Stratégie: {strategy}, échantillon: {target_size}/{len(all_files)}"
            )

            if strategy == "random":
                selected_files = self._random_sample(all_files, target_size)
            elif strategy == "stratified":
                selected_files = self._stratified_sample(all_files, target_size)
            else:
                raise ValueError(f"Stratégie inconnue: {strategy}")

        # Parser les notes
        logger.info(f"Parsing de {len(selected_files)} notes...")

        notes = []
        errors = 0

        for file_path in selected_files:
            try:
                note = self.parse_note(file_path)
                notes.append(note)
            except Exception as e:
                logger.error(f"Erreur sur {file_path}: {e}")
                errors += 1

        logger.info(
            f"Parsing terminé: {len(notes)} notes réussies, {errors} erreurs"
        )

        return notes

    def _random_sample(self, files: List[Path], sample_size: int) -> List[Path]:
        """
        Échantillonnage aléatoire simple.

        Args:
            files: Liste complète des fichiers
            sample_size: Taille de l'échantillon

        Returns:
            List[Path]: Échantillon aléatoire
        """
        return random.sample(files, min(sample_size, len(files)))

    def _stratified_sample(self, files: List[Path], sample_size: int) -> List[Path]:
        """
        Échantillonnage stratifié par dossier.

        Chaque dossier contribue proportionnellement à sa taille.

        Args:
            files: Liste complète des fichiers
            sample_size: Taille de l'échantillon

        Returns:
            List[Path]: Échantillon stratifié
        """
        # Grouper par dossier
        folders: Dict[str, List[Path]] = {}

        for file_path in files:
            relative_path = file_path.relative_to(self.vault_path)
            folder = str(relative_path.parent)

            if folder not in folders:
                folders[folder] = []

            folders[folder].append(file_path)

        # Calculer la proportion de chaque dossier
        total_files = len(files)
        selected_files = []

        for folder, folder_files in folders.items():
            folder_proportion = len(folder_files) / total_files
            folder_sample_size = max(1, int(sample_size * folder_proportion))

            # Échantillonner ce dossier
            folder_sample = random.sample(
                folder_files, min(folder_sample_size, len(folder_files))
            )

            selected_files.extend(folder_sample)

            logger.debug(
                f"Dossier '{folder}': {len(folder_sample)}/{len(folder_files)} notes"
            )

        # Si on dépasse la taille cible, tronquer aléatoirement
        if len(selected_files) > sample_size:
            selected_files = random.sample(selected_files, sample_size)

        return selected_files

    def save_cache(self, notes: List[Note]) -> None:
        """
        Sauvegarde les notes dans le cache JSON.

        Args:
            notes: Liste des notes à sauvegarder
        """
        logger.info(f"Sauvegarde du cache: {len(notes)} notes")

        try:
            # Convertir en dictionnaire avec mode='json' pour sérialiser les datetime
            notes_data = [note.model_dump(mode='json') for note in notes]

            # Sauvegarder
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "cached_at": datetime.now().isoformat(),
                        "count": len(notes),
                        "notes": notes_data,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            logger.info(f"Cache sauvegardé: {self.cache_path}")

        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du cache: {e}")

    def load_cache(self) -> Optional[List[Note]]:
        """
        Charge les notes depuis le cache JSON.

        Returns:
            Optional[List[Note]]: Liste des notes ou None si le cache n'existe pas

        Raises:
            ValueError: Si le cache est invalide
        """
        if not self.cache_path.exists():
            logger.info("Pas de cache existant")
            return None

        logger.info(f"Chargement du cache: {self.cache_path}")

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            notes_data = cache_data.get("notes", [])
            cached_at = cache_data.get("cached_at")

            logger.info(
                f"Cache chargé: {len(notes_data)} notes (cached at: {cached_at})"
            )

            # Convertir en objets Note (model_validate gère les datetime ISO)
            notes = [Note.model_validate(note_dict) for note_dict in notes_data]

            return notes

        except Exception as e:
            logger.error(f"Erreur lors du chargement du cache: {e}")
            raise ValueError(f"Cache invalide: {e}") from e

    def detect_new_notes(self, cached_notes: List[Note]) -> List[Path]:
        """
        Détecte les notes nouvelles (pas dans le cache).

        Args:
            cached_notes: Liste des notes en cache

        Returns:
            List[Path]: Chemins des notes nouvelles
        """
        # IDs des notes en cache
        cached_ids = {note.id for note in cached_notes}

        # Scanner le vault
        all_files = self.scan_vault()

        new_files = []

        for file_path in all_files:
            relative_path = file_path.relative_to(self.vault_path)
            note_id = self._generate_note_id(str(relative_path))

            if note_id not in cached_ids:
                new_files.append(file_path)

        logger.info(f"Détection: {len(new_files)} nouvelles notes")

        return new_files

    def detect_modified_notes(self, cached_notes: List[Note]) -> List[Path]:
        """
        Détecte les notes modifiées (modified_at différent du cache).

        Args:
            cached_notes: Liste des notes en cache

        Returns:
            List[Path]: Chemins des notes modifiées
        """
        # Créer un mapping id -> modified_at
        cached_modified = {
            note.id: note.modified_at for note in cached_notes if note.modified_at
        }

        modified_files = []

        for note in cached_notes:
            file_path = Path(note.file_path)

            if not file_path.exists():
                continue

            # Comparer la date de modification
            file_stat = file_path.stat()
            file_modified = datetime.fromtimestamp(file_stat.st_mtime)

            cached_modified_date = cached_modified.get(note.id)

            if cached_modified_date and file_modified > cached_modified_date:
                modified_files.append(file_path)

        logger.info(f"Détection: {len(modified_files)} notes modifiées")

        return modified_files

    def detect_deleted_notes(self, cached_notes: List[Note]) -> List[Note]:
        """
        Détecte les notes supprimées (présentes dans le cache mais plus dans le vault).

        Args:
            cached_notes: Liste des notes en cache

        Returns:
            List[Note]: Notes qui ont été supprimées du vault
        """
        # Scanner le vault pour obtenir tous les fichiers existants
        all_files = self.scan_vault()

        # Créer un set des IDs actuels dans le vault
        current_ids = set()
        for file_path in all_files:
            relative_path = file_path.relative_to(self.vault_path)
            note_id = self._generate_note_id(str(relative_path))
            current_ids.add(note_id)

        # Trouver les notes en cache qui ne sont plus dans le vault
        deleted_notes = []

        for note in cached_notes:
            if note.id not in current_ids:
                deleted_notes.append(note)

        logger.info(f"Détection: {len(deleted_notes)} notes supprimées")

        return deleted_notes

    def __repr__(self) -> str:
        """Représentation string du scanner."""
        return (
            f"NoteScanner(vault='{self.vault_path}', "
            f"exclusions={self.exclude_folders})"
        )
