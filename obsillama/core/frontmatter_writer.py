"""
ObsIllama - Frontmatter Writer

Ce module gère l'écriture et la modification du frontmatter YAML dans les notes Obsidian.
Il utilise ruamel.yaml pour préserver l'ordre, les commentaires et le style YAML.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from obsillama.models.category import Category
from obsillama.models.note import Note

# Configuration du logger
logger = logging.getLogger(__name__)


class FrontmatterWriter:
    """
    Classe pour écrire et modifier le frontmatter YAML des notes Obsidian.

    Utilise ruamel.yaml pour préserver:
    - L'ordre des clés
    - Les commentaires YAML
    - Les quotes et le style
    - Les sauts de ligne

    Features:
    - Backup automatique avant modification
    - Merge intelligent des tags
    - Ajout de métadonnées AI
    - Préservation de la structure YAML
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Initialise le FrontmatterWriter.

        Args:
            backup_dir: Dossier de backup (défaut: .obsillama_backups/)
        """
        self.backup_dir = backup_dir or Path(".obsillama_backups")
        self.yaml = YAML()
        # Préserver le style YAML existant
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self.yaml.width = 4096  # Éviter le line wrap

        logger.debug(f"FrontmatterWriter initialisé avec backup_dir={self.backup_dir}")

    def parse_note_file(self, file_path: Path) -> tuple[CommentedMap, str, str]:
        """
        Parse un fichier note et extrait le frontmatter avec ruamel.yaml.

        Cette méthode préserve la structure YAML complète pour permettre
        une modification sans perte de formatage.

        Args:
            file_path: Chemin vers le fichier .md

        Returns:
            Tuple[CommentedMap, str, str]:
                - frontmatter (dict-like avec structure préservée)
                - contenu sans frontmatter
                - contenu brut complet

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le YAML est invalide
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")

        # Lire le contenu brut
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # Vérifier s'il y a du frontmatter (commence par ---)
        if not raw_content.strip().startswith("---"):
            logger.debug(f"Pas de frontmatter dans {file_path.name}")
            return CommentedMap(), raw_content, raw_content

        # Séparer frontmatter et contenu
        # Pattern: --- (frontmatter) --- (contenu)
        parts = raw_content.split("---", 2)

        if len(parts) < 3:
            # Frontmatter incomplet ou malformé
            logger.warning(f"Frontmatter malformé dans {file_path.name}")
            return CommentedMap(), raw_content, raw_content

        frontmatter_str = parts[1].strip()
        content = parts[2].lstrip()

        # Parser le frontmatter avec ruamel.yaml
        try:
            frontmatter = self.yaml.load(frontmatter_str) or CommentedMap()
            if not isinstance(frontmatter, CommentedMap):
                frontmatter = CommentedMap(frontmatter)
        except Exception as e:
            logger.error(f"Erreur parsing YAML dans {file_path.name}: {e}")
            raise ValueError(f"YAML invalide: {e}")

        logger.debug(
            f"Frontmatter parsé: {len(frontmatter)} champs, "
            f"contenu: {len(content)} caractères"
        )

        return frontmatter, content, raw_content

    def create_frontmatter_if_missing(self) -> CommentedMap:
        """
        Crée un frontmatter vide avec structure préservée.

        Returns:
            CommentedMap: Frontmatter vide (dict-like)
        """
        return CommentedMap()

    def backup_note(self, file_path: Path) -> Path:
        """
        Crée un backup de la note avant modification.

        Le backup est stocké dans:
        .obsillama_backups/YYYYMMDD_HHMMSS/path/to/note.md

        Args:
            file_path: Chemin vers la note à backup

        Returns:
            Path: Chemin du fichier de backup créé

        Raises:
            IOError: Si le backup échoue
        """
        # Créer un snapshot avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = self.backup_dir / timestamp

        # Créer le dossier de backup
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Copier le fichier en préservant le nom
        backup_path = snapshot_dir / file_path.name

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup créé: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erreur lors du backup de {file_path}: {e}")
            raise IOError(f"Échec backup: {e}")

    def update_frontmatter(
        self,
        file_path: Path,
        categories: List[Category],
        confidence: float,
        backup: bool = True
    ) -> None:
        """
        Met à jour le frontmatter d'une note avec les catégories AI.

        Modifications apportées:
        - Ajoute les tags AI-Category-{tag_name} à la liste tags (merge)
        - Ajoute le champ ai_categories (liste des noms de catégories)
        - Ajoute le champ ai_confidence (score)
        - Ajoute le champ ai_processed_date (timestamp ISO 8601)

        Args:
            file_path: Chemin vers la note
            categories: Liste des catégories à assigner
            confidence: Score de confiance (0.0 - 1.0)
            backup: Si True, crée un backup avant modification

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le YAML est invalide
            IOError: Si l'écriture échoue
        """
        # Backup si demandé
        if backup:
            self.backup_note(file_path)

        # Parser le fichier
        frontmatter, content, raw_content = self.parse_note_file(file_path)

        # Si pas de frontmatter, en créer un
        if not frontmatter:
            frontmatter = self.create_frontmatter_if_missing()

        # 1. Merger les tags AI avec les tags existants
        existing_tags = frontmatter.get("tags", [])

        # Normaliser les tags existants (peut être string ou list)
        if isinstance(existing_tags, str):
            existing_tags = [t.strip() for t in existing_tags.split(",")]
        elif not isinstance(existing_tags, list):
            existing_tags = []

        # Créer les nouveaux tags AI
        ai_tags = [f"AI-Category-{cat.tag_name}" for cat in categories]

        # Merger (sans doublons)
        all_tags = list(set(existing_tags + ai_tags))
        frontmatter["tags"] = all_tags

        # 2. Ajouter les métadonnées AI
        frontmatter["ai_categories"] = [cat.name for cat in categories]
        frontmatter["ai_confidence"] = round(confidence, 4)
        frontmatter["ai_processed_date"] = datetime.now().isoformat()

        logger.info(
            f"Frontmatter mis à jour: {len(all_tags)} tags, "
            f"{len(categories)} catégories, confidence={confidence:.2f}"
        )

        # 3. Écrire le fichier avec le nouveau frontmatter
        self._write_note_with_frontmatter(file_path, frontmatter, content)

    def apply_categories_to_note(
        self,
        note: Note,
        categories: List[Category],
        confidence: float = 0.0,
        backup: bool = True
    ) -> None:
        """
        Applique les catégories à une note (wrapper de update_frontmatter).

        Args:
            note: Objet Note à modifier
            categories: Liste des catégories à assigner
            confidence: Score de confiance (optionnel)
            backup: Si True, crée un backup avant modification

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le YAML est invalide
            IOError: Si l'écriture échoue
        """
        file_path = Path(note.file_path)
        self.update_frontmatter(file_path, categories, confidence, backup=backup)

        logger.info(f"Catégories appliquées à la note: {note.title}")

    def remove_ai_metadata(self, file_path: Path, backup: bool = True) -> None:
        """
        Supprime les métadonnées AI du frontmatter (cleanup).

        Supprime:
        - Tags AI-Category-*
        - Champ ai_categories
        - Champ ai_confidence
        - Champ ai_processed_date

        Args:
            file_path: Chemin vers la note
            backup: Si True, crée un backup avant modification

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le YAML est invalide
            IOError: Si l'écriture échoue
        """
        # Backup si demandé
        if backup:
            self.backup_note(file_path)

        # Parser le fichier
        frontmatter, content, raw_content = self.parse_note_file(file_path)

        if not frontmatter:
            logger.debug(f"Pas de frontmatter à nettoyer dans {file_path.name}")
            return

        # 1. Supprimer les tags AI-Category-*
        existing_tags = frontmatter.get("tags", [])

        if isinstance(existing_tags, list):
            cleaned_tags = [
                tag for tag in existing_tags
                if not str(tag).startswith("AI-Category-")
            ]
            frontmatter["tags"] = cleaned_tags

        # 2. Supprimer les champs AI
        frontmatter.pop("ai_categories", None)
        frontmatter.pop("ai_confidence", None)
        frontmatter.pop("ai_processed_date", None)

        logger.info(f"Métadonnées AI supprimées de {file_path.name}")

        # 3. Écrire le fichier nettoyé
        self._write_note_with_frontmatter(file_path, frontmatter, content)

    def _write_note_with_frontmatter(
        self,
        file_path: Path,
        frontmatter: CommentedMap,
        content: str
    ) -> None:
        """
        Écrit une note avec le frontmatter mis à jour.

        Reconstruit le fichier au format:
        ---
        (frontmatter YAML)
        ---
        (contenu markdown)

        Args:
            file_path: Chemin vers le fichier
            frontmatter: Frontmatter à écrire
            content: Contenu markdown (sans frontmatter)

        Raises:
            IOError: Si l'écriture échoue
        """
        try:
            # Sérialiser le frontmatter en YAML
            from io import StringIO
            stream = StringIO()
            self.yaml.dump(frontmatter, stream)
            yaml_str = stream.getvalue()

            # Construire le contenu complet
            # Format: ---\n(yaml)\n---\n(content)
            full_content = f"---\n{yaml_str}---\n{content}"

            # Écrire le fichier
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            logger.debug(f"Fichier écrit: {file_path}")

        except Exception as e:
            logger.error(f"Erreur lors de l'écriture de {file_path}: {e}")
            raise IOError(f"Échec écriture: {e}")
