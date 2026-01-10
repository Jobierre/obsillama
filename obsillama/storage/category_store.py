"""
ObsIllama - Category Store

Ce module gère le stockage et la récupération des catégories et assignations.
Il sauvegarde la taxonomie en JSON et dans LanceDB.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from obsillama.models.category import Category, ReviewStatus
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.config.settings import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# CategoryStore
# =============================================================================


class CategoryStore:
    """
    Gestionnaire de stockage pour les catégories et assignations.

    Ce store gère :
    - Taxonomie : sauvegarde/chargement des catégories (JSON + LanceDB)
    - Assignations : mapping note_id → category_id avec confiance (JSON)
    - Historique : versions de la taxonomie

    Attributes:
        db_manager: Manager LanceDB
        taxonomy_file: Fichier JSON de la taxonomie
        assignments_file: Fichier JSON des assignations
    """

    def __init__(
        self,
        db_manager: Optional[LanceDBManager] = None,
        taxonomy_file: Optional[str] = None,
        assignments_file: Optional[str] = None,
    ):
        """
        Initialise le CategoryStore.

        Args:
            db_manager: Manager LanceDB (créé si None)
            taxonomy_file: Chemin du fichier JSON de taxonomie
            assignments_file: Chemin du fichier JSON des assignations
        """
        self.db_manager = db_manager or LanceDBManager()

        # Dossier de stockage
        categories_dir = Path("data/categories")
        categories_dir.mkdir(parents=True, exist_ok=True)

        # Fichiers
        if taxonomy_file:
            self.taxonomy_file = Path(taxonomy_file)
        else:
            self.taxonomy_file = categories_dir / "taxonomy.json"

        if assignments_file:
            self.assignments_file = Path(assignments_file)
        else:
            self.assignments_file = categories_dir / "assignments.json"

        logger.info(f"CategoryStore initialisé")
        logger.info(f"  Taxonomie : {self.taxonomy_file}")
        logger.info(f"  Assignations : {self.assignments_file}")

    # =========================================================================
    # Sauvegarde - Taxonomie
    # =========================================================================

    def save_taxonomy(
        self,
        categories: List[Category],
        version: Optional[str] = None,
    ) -> None:
        """
        Sauvegarde la taxonomie (liste des catégories) en JSON.

        Args:
            categories: Liste des catégories
            version: Version optionnelle (auto si None)
        """
        logger.info(f"Sauvegarde de la taxonomie : {len(categories)} catégories")

        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            # Convertir en dictionnaires
            categories_data = [cat.model_dump(mode='json') for cat in categories]

            # Préparer les données
            taxonomy_data = {
                "version": version,
                "created_at": datetime.now().isoformat(),
                "category_count": len(categories),
                "categories": categories_data,
            }

            # Sauvegarder en JSON
            with open(self.taxonomy_file, "w", encoding="utf-8") as f:
                json.dump(taxonomy_data, f, indent=2, ensure_ascii=False)

            logger.info(
                f"  → Taxonomie sauvegardée : {self.taxonomy_file} (version {version})"
            )

            # Sauvegarder aussi dans LanceDB (avec embeddings si disponibles)
            # Pour l'instant on sauvegarde juste en JSON
            # TODO: Sauvegarder dans LanceDB si on a les embeddings

        except Exception as e:
            logger.error(f"Erreur sauvegarde taxonomie : {e}")
            raise

    def load_taxonomy(self) -> List[Category]:
        """
        Charge la taxonomie depuis le fichier JSON.

        Returns:
            Liste des catégories

        Raises:
            ValueError: Si le fichier n'existe pas ou est invalide
        """
        logger.info(f"Chargement de la taxonomie depuis {self.taxonomy_file}")

        if not self.taxonomy_file.exists():
            logger.warning("Fichier de taxonomie n'existe pas")
            return []

        try:
            # Charger le JSON
            with open(self.taxonomy_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            categories_data = data.get("categories", [])

            # Convertir en objets Category
            categories = []
            for cat_data in categories_data:
                # Convertir les enums
                if isinstance(cat_data.get("review_status"), str):
                    cat_data["review_status"] = ReviewStatus(
                        cat_data["review_status"]
                    )

                # Convertir les dates
                if isinstance(cat_data.get("created_at"), str):
                    cat_data["created_at"] = datetime.fromisoformat(
                        cat_data["created_at"]
                    )

                category = Category(**cat_data)
                categories.append(category)

            logger.info(
                f"  → {len(categories)} catégories chargées (version {data.get('version', 'unknown')})"
            )
            return categories

        except Exception as e:
            logger.error(f"Erreur chargement taxonomie : {e}")
            raise ValueError(f"Impossible de charger la taxonomie : {e}")

    # =========================================================================
    # Sauvegarde - Assignations
    # =========================================================================

    def save_assignments(
        self, assignments: Dict[str, List[Tuple[str, float]]]
    ) -> None:
        """
        Sauvegarde les assignations note → catégorie.

        Args:
            assignments: Dict {category_id: [(note_id, confidence), ...]}
        """
        logger.info(
            f"Sauvegarde des assignations : "
            f"{len(assignments)} catégories, "
            f"{sum(len(v) for v in assignments.values())} notes"
        )

        try:
            # Convertir en format JSON-friendly
            assignments_data = {}
            for category_id, notes_list in assignments.items():
                assignments_data[category_id] = [
                    {"note_id": note_id, "confidence": confidence}
                    for note_id, confidence in notes_list
                ]

            # Préparer les données
            data = {
                "saved_at": datetime.now().isoformat(),
                "category_count": len(assignments),
                "note_count": sum(len(v) for v in assignments.values()),
                "assignments": assignments_data,
            }

            # Sauvegarder en JSON
            with open(self.assignments_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"  → Assignations sauvegardées : {self.assignments_file}")

        except Exception as e:
            logger.error(f"Erreur sauvegarde assignations : {e}")
            raise

    def load_assignments(self) -> Dict[str, List[Tuple[str, float]]]:
        """
        Charge les assignations depuis le fichier JSON.

        Returns:
            Dict {category_id: [(note_id, confidence), ...]}

        Raises:
            ValueError: Si le fichier n'existe pas
        """
        logger.info(f"Chargement des assignations depuis {self.assignments_file}")

        if not self.assignments_file.exists():
            logger.warning("Fichier d'assignations n'existe pas")
            return {}

        try:
            # Charger le JSON
            with open(self.assignments_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assignments_data = data.get("assignments", {})

            # Convertir en format Python
            assignments = {}
            for category_id, notes_list in assignments_data.items():
                assignments[category_id] = [
                    (item["note_id"], item["confidence"]) for item in notes_list
                ]

            logger.info(
                f"  → {len(assignments)} catégories chargées, "
                f"{sum(len(v) for v in assignments.values())} notes"
            )
            return assignments

        except Exception as e:
            logger.error(f"Erreur chargement assignations : {e}")
            raise ValueError(f"Impossible de charger les assignations : {e}")

    # =========================================================================
    # Mise à jour
    # =========================================================================

    def update_category(
        self, category_id: str, updates: Dict[str, any]
    ) -> Optional[Category]:
        """
        Met à jour une catégorie dans la taxonomie.

        Args:
            category_id: ID de la catégorie
            updates: Dictionnaire des champs à mettre à jour

        Returns:
            Catégorie mise à jour ou None si non trouvée
        """
        logger.info(f"Mise à jour catégorie {category_id}")

        # Charger la taxonomie
        categories = self.load_taxonomy()

        # Trouver la catégorie
        category = next((c for c in categories if c.id == category_id), None)

        if not category:
            logger.warning(f"Catégorie {category_id} non trouvée")
            return None

        # Appliquer les mises à jour
        for key, value in updates.items():
            if hasattr(category, key):
                setattr(category, key, value)

        # Sauvegarder
        self.save_taxonomy(categories)

        logger.info(f"  → Catégorie {category_id} mise à jour")
        return category

    def approve_category(self, category_id: str) -> Optional[Category]:
        """
        Approuve une catégorie (change son statut à APPROVED).

        Args:
            category_id: ID de la catégorie

        Returns:
            Catégorie approuvée ou None
        """
        return self.update_category(
            category_id, {"review_status": ReviewStatus.APPROVED}
        )

    def reject_category(self, category_id: str) -> Optional[Category]:
        """
        Rejette une catégorie (change son statut à REJECTED).

        Args:
            category_id: ID de la catégorie

        Returns:
            Catégorie rejetée ou None
        """
        return self.update_category(
            category_id, {"review_status": ReviewStatus.REJECTED}
        )

    # =========================================================================
    # Utilitaires
    # =========================================================================

    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """
        Récupère une catégorie par son ID.

        Args:
            category_id: ID de la catégorie

        Returns:
            Catégorie ou None si non trouvée
        """
        categories = self.load_taxonomy()
        return next((c for c in categories if c.id == category_id), None)

    def get_approved_categories(self) -> List[Category]:
        """
        Récupère uniquement les catégories approuvées.

        Returns:
            Liste des catégories approuvées
        """
        categories = self.load_taxonomy()
        return [c for c in categories if c.review_status == ReviewStatus.APPROVED]

    def get_notes_for_category(
        self, category_id: str
    ) -> List[Tuple[str, float]]:
        """
        Récupère les notes assignées à une catégorie.

        Args:
            category_id: ID de la catégorie

        Returns:
            Liste de (note_id, confidence)
        """
        assignments = self.load_assignments()
        return assignments.get(category_id, [])

    def get_stats(self) -> Dict[str, any]:
        """
        Récupère des statistiques sur la taxonomie.

        Returns:
            Dictionnaire de statistiques
        """
        categories = self.load_taxonomy()
        assignments = self.load_assignments()

        return {
            "total_categories": len(categories),
            "approved_categories": len(
                [c for c in categories if c.review_status == ReviewStatus.APPROVED]
            ),
            "pending_categories": len(
                [c for c in categories if c.review_status == ReviewStatus.PENDING]
            ),
            "rejected_categories": len(
                [c for c in categories if c.review_status == ReviewStatus.REJECTED]
            ),
            "total_assignments": sum(len(v) for v in assignments.values()),
            "avg_notes_per_category": (
                sum(len(v) for v in assignments.values()) / len(assignments)
                if assignments
                else 0
            ),
        }

    def clear(self) -> None:
        """
        Supprime toutes les données (taxonomie et assignations).

        ATTENTION : Cette opération est irréversible !
        """
        logger.warning("Suppression de toutes les données du CategoryStore")

        try:
            if self.taxonomy_file.exists():
                self.taxonomy_file.unlink()
                logger.info(f"  → {self.taxonomy_file} supprimé")

            if self.assignments_file.exists():
                self.assignments_file.unlink()
                logger.info(f"  → {self.assignments_file} supprimé")

            logger.info("CategoryStore complètement vidé")

        except Exception as e:
            logger.error(f"Erreur suppression données : {e}")
            raise
