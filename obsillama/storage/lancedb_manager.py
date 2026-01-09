"""
ObsIllama - LanceDB Manager

Ce module gère la connexion à LanceDB et toutes les opérations sur les tables.
Il fournit des méthodes pour créer, insérer, récupérer et rechercher des données.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import lancedb
from lancedb.pydantic import LanceModel, Vector
import pyarrow as pa

from obsillama.config.settings import get_settings
from obsillama.models.note import Note
from obsillama.models.category import Category

# Configuration du logger
logger = logging.getLogger(__name__)


# ============================================================================
# Schémas LanceDB (basés sur Pydantic)
# ============================================================================


class NoteRecord(LanceModel):
    """Schéma pour les notes dans LanceDB."""

    # Identifiants
    id: str
    file_path: str
    file_name: str
    relative_path: str

    # Contenu
    title: str
    content: str
    word_count: int

    # Tags et métadonnées
    tags: List[str]
    folder: str

    # Dates (stockées comme timestamps ISO)
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    scanned_at: str

    # Embedding vectoriel (768 dimensions pour nomic-embed-text)
    vector: Vector(768)

    # Catégorisation IA
    ai_categories: List[str] = []
    ai_confidence: Optional[float] = None
    ai_processed: bool = False


class CategoryRecord(LanceModel):
    """Schéma pour les catégories dans LanceDB."""

    # Identifiants
    id: str
    name: str
    tag_name: str

    # Description
    description: str
    keywords: List[str]

    # Hiérarchie
    parent_id: Optional[str] = None
    children_ids: List[str] = []
    level: int

    # Statistiques
    note_count: int
    avg_confidence: float

    # Métadonnées
    created_at: str
    review_status: str  # "pending", "approved", "rejected"

    # Embedding vectoriel de la catégorie
    vector: Vector(768)


class EntityRecord(LanceModel):
    """Schéma pour les entités GraphRAG dans LanceDB."""

    # Identifiants
    id: str
    name: str
    entity_type: str  # "technology", "concept", "tool", etc.

    # Description
    description: str

    # Relations
    note_ids: List[str]  # Notes où cette entité apparaît

    # Statistiques
    frequency: int  # Nombre d'apparitions
    importance_score: float

    # Métadonnées
    created_at: str

    # Embedding vectoriel de l'entité
    vector: Vector(768)


class CommunityRecord(LanceModel):
    """Schéma pour les communautés GraphRAG dans LanceDB."""

    # Identifiants
    id: str
    name: str

    # Description générée par LLM
    description: str
    summary: str

    # Membres
    entity_ids: List[str]
    note_ids: List[str]

    # Statistiques
    size: int
    density: float

    # Métadonnées
    created_at: str
    algorithm: str  # "leiden", "louvain"

    # Embedding vectoriel de la communauté
    vector: Vector(768)


# ============================================================================
# LanceDB Manager
# ============================================================================


class LanceDBManager:
    """
    Manager pour toutes les opérations LanceDB.

    Cette classe gère:
    - Connexion à la base de données LanceDB
    - Création des tables (notes, categories, entities, communities)
    - Insertion et mise à jour des données
    - Recherche vectorielle
    - Création d'index vectoriels

    Attributes:
        db_path: Chemin vers la base de données
        db: Connexion LanceDB
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialise le manager LanceDB.

        Args:
            db_path: Chemin vers la DB (défaut: depuis config)
        """
        settings = get_settings()

        self.db_path = Path(db_path or settings.lancedb.path)
        self.embedding_dim = settings.lancedb.embedding_dim

        # Créer le dossier si nécessaire
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Se connecter à LanceDB
        self.db = lancedb.connect(str(self.db_path))

        logger.info(f"LanceDBManager initialisé: {self.db_path}")

    # ========================================================================
    # Création des tables
    # ========================================================================

    def create_notes_table(self, mode: str = "create") -> None:
        """
        Crée la table des notes.

        Args:
            mode: Mode de création ("create", "overwrite")

        Raises:
            ValueError: Si la table existe déjà en mode "create"
        """
        logger.info("Création de la table 'notes'")

        try:
            self.db.create_table("notes", schema=NoteRecord, mode=mode)
            logger.info("Table 'notes' créée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table 'notes': {e}")
            raise

    def create_categories_table(self, mode: str = "create") -> None:
        """
        Crée la table des catégories.

        Args:
            mode: Mode de création ("create", "overwrite")
        """
        logger.info("Création de la table 'categories'")

        try:
            self.db.create_table("categories", schema=CategoryRecord, mode=mode)
            logger.info("Table 'categories' créée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table 'categories': {e}")
            raise

    def create_entities_table(self, mode: str = "create") -> None:
        """
        Crée la table des entités GraphRAG.

        Args:
            mode: Mode de création ("create", "overwrite")
        """
        logger.info("Création de la table 'entities'")

        try:
            self.db.create_table("entities", schema=EntityRecord, mode=mode)
            logger.info("Table 'entities' créée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table 'entities': {e}")
            raise

    def create_communities_table(self, mode: str = "create") -> None:
        """
        Crée la table des communautés GraphRAG.

        Args:
            mode: Mode de création ("create", "overwrite")
        """
        logger.info("Création de la table 'communities'")

        try:
            self.db.create_table("communities", schema=CommunityRecord, mode=mode)
            logger.info("Table 'communities' créée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table 'communities': {e}")
            raise

    def create_all_tables(self, mode: str = "create") -> None:
        """
        Crée toutes les tables.

        Args:
            mode: Mode de création ("create", "overwrite")
        """
        logger.info("Création de toutes les tables")

        self.create_notes_table(mode=mode)
        self.create_categories_table(mode=mode)
        self.create_entities_table(mode=mode)
        self.create_communities_table(mode=mode)

        logger.info("Toutes les tables créées")

    # ========================================================================
    # Insertion de données - Notes
    # ========================================================================

    def insert_notes(
        self, notes: List[Note], embeddings: List[List[float]]
    ) -> None:
        """
        Insère des notes dans la table avec leurs embeddings.

        Args:
            notes: Liste des notes à insérer
            embeddings: Liste des embeddings (même ordre que notes)

        Raises:
            ValueError: Si le nombre de notes != nombre d'embeddings
        """
        if len(notes) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(notes)} notes vs {len(embeddings)} embeddings"
            )

        logger.info(f"Insertion de {len(notes)} notes dans LanceDB")

        try:
            # Ouvrir la table
            table = self.db.open_table("notes")

            # Convertir les notes en records LanceDB
            records = []
            for note, embedding in zip(notes, embeddings):
                record = NoteRecord(
                    id=note.id,
                    file_path=note.file_path,
                    file_name=note.file_name,
                    relative_path=note.relative_path,
                    title=note.title,
                    content=note.content,
                    word_count=note.word_count,
                    tags=note.tags,
                    folder=note.folder,
                    created_at=note.created_at.isoformat() if note.created_at else None,
                    modified_at=note.modified_at.isoformat()
                    if note.modified_at
                    else None,
                    scanned_at=note.scanned_at.isoformat(),
                    vector=embedding,
                    ai_categories=note.ai_categories,
                    ai_confidence=note.ai_confidence,
                    ai_processed=note.ai_processed,
                )
                records.append(record)

            # Insérer
            table.add(records)

            logger.info(f"{len(records)} notes insérées avec succès")

        except Exception as e:
            logger.error(f"Erreur lors de l'insertion des notes: {e}")
            raise

    def insert_categories(
        self, categories: List[Category], embeddings: List[List[float]]
    ) -> None:
        """
        Insère des catégories dans la table avec leurs embeddings.

        Args:
            categories: Liste des catégories à insérer
            embeddings: Liste des embeddings (même ordre que categories)
        """
        if len(categories) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(categories)} categories vs {len(embeddings)} embeddings"
            )

        logger.info(f"Insertion de {len(categories)} catégories dans LanceDB")

        try:
            table = self.db.open_table("categories")

            records = []
            for category, embedding in zip(categories, embeddings):
                record = CategoryRecord(
                    id=category.id,
                    name=category.name,
                    tag_name=category.tag_name,
                    description=category.description,
                    keywords=category.keywords,
                    parent_id=category.parent_id,
                    children_ids=category.children_ids,
                    level=category.level,
                    note_count=category.note_count,
                    avg_confidence=category.avg_confidence,
                    created_at=category.created_at.isoformat(),
                    review_status=category.review_status.value if hasattr(category.review_status, 'value') else str(category.review_status),
                    vector=embedding,
                )
                records.append(record)

            table.add(records)

            logger.info(f"{len(records)} catégories insérées avec succès")

        except Exception as e:
            logger.error(f"Erreur lors de l'insertion des catégories: {e}")
            raise

    # ========================================================================
    # Récupération de données
    # ========================================================================

    def get_note_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une note par son ID.

        Args:
            note_id: ID de la note

        Returns:
            Optional[Dict]: Dictionnaire de la note ou None
        """
        logger.debug(f"Récupération de la note: {note_id}")

        try:
            table = self.db.open_table("notes")

            # Rechercher par ID
            results = (
                table.search()
                .where(f"id = '{note_id}'")
                .limit(1)
                .to_list()
            )

            if results:
                return results[0]
            else:
                logger.warning(f"Note non trouvée: {note_id}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la note: {e}")
            return None

    def get_all_notes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère toutes les notes.

        Args:
            limit: Nombre maximum de notes à retourner

        Returns:
            List[Dict]: Liste des notes
        """
        logger.info(f"Récupération de toutes les notes (limit={limit})")

        try:
            table = self.db.open_table("notes")

            query = table.search()

            if limit:
                query = query.limit(limit)

            results = query.to_list()

            logger.info(f"{len(results)} notes récupérées")

            return results

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des notes: {e}")
            return []

    def get_notes_by_ids(self, note_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Récupère plusieurs notes par leurs IDs.

        Args:
            note_ids: Liste des IDs

        Returns:
            List[Dict]: Liste des notes trouvées
        """
        logger.debug(f"Récupération de {len(note_ids)} notes")

        results = []
        for note_id in note_ids:
            note = self.get_note_by_id(note_id)
            if note:
                results.append(note)

        return results

    # ========================================================================
    # Recherche vectorielle
    # ========================================================================

    def search_notes_by_embedding(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique de notes par embedding.

        Args:
            query_embedding: Vecteur de requête (768 dims)
            limit: Nombre de résultats à retourner
            filter_query: Filtre SQL optionnel (ex: "word_count > 100")

        Returns:
            List[Dict]: Liste des notes similaires avec score

        Example:
            >>> results = manager.search_notes_by_embedding(
            ...     query_embedding=[0.1, 0.2, ...],
            ...     limit=5,
            ...     filter_query="folder = 'Projects'"
            ... )
        """
        logger.info(f"Recherche vectorielle (limit={limit}, filter={bool(filter_query)})")

        try:
            table = self.db.open_table("notes")

            # Construire la requête
            query = table.search(query_embedding).limit(limit)

            if filter_query:
                query = query.where(filter_query)

            results = query.to_list()

            logger.info(f"{len(results)} résultats trouvés")

            return results

        except Exception as e:
            logger.error(f"Erreur lors de la recherche vectorielle: {e}")
            return []

    # ========================================================================
    # Gestion des index vectoriels
    # ========================================================================

    def create_vector_index(
        self,
        table_name: str,
        column_name: str = "vector",
        metric: str = "cosine",
    ) -> None:
        """
        Crée un index vectoriel IVF_PQ pour accélérer les recherches.

        Args:
            table_name: Nom de la table
            column_name: Nom de la colonne vectorielle
            metric: Métrique de distance ("cosine", "l2", "dot")
        """
        logger.info(
            f"Création d'index vectoriel sur {table_name}.{column_name} (metric={metric})"
        )

        try:
            settings = get_settings()

            table = self.db.open_table(table_name)

            # Créer l'index IVF_PQ
            table.create_index(
                metric=metric,
                vector_column_name=column_name,
                num_partitions=settings.lancedb.index_params.num_partitions,
                num_sub_vectors=settings.lancedb.index_params.num_sub_vectors,
            )

            logger.info(f"Index créé avec succès sur {table_name}.{column_name}")

        except Exception as e:
            logger.error(f"Erreur lors de la création de l'index: {e}")
            raise

    def create_all_indexes(self) -> None:
        """Crée les index vectoriels pour toutes les tables."""
        logger.info("Création de tous les index vectoriels")

        tables = ["notes", "categories", "entities", "communities"]

        for table_name in tables:
            try:
                self.create_vector_index(table_name)
            except Exception as e:
                logger.warning(f"Index non créé pour {table_name}: {e}")

        logger.info("Création des index terminée")

    # ========================================================================
    # Utilitaires
    # ========================================================================

    def list_tables(self) -> List[str]:
        """Liste toutes les tables dans la base de données."""
        try:
            result = self.db.list_tables()
            # list_tables() peut retourner un objet avec attribut tables
            if hasattr(result, 'tables'):
                return result.tables
            return result
        except AttributeError:
            # Fallback pour anciennes versions
            return self.db.table_names()

    def table_exists(self, table_name: str) -> bool:
        """Vérifie si une table existe."""
        return table_name in self.list_tables()

    def count_records(self, table_name: str) -> int:
        """Compte le nombre de records dans une table."""
        try:
            table = self.db.open_table(table_name)
            return table.count_rows()
        except Exception as e:
            logger.error(f"Erreur lors du comptage: {e}")
            return 0

    def drop_table(self, table_name: str) -> None:
        """Supprime une table."""
        logger.warning(f"Suppression de la table: {table_name}")
        self.db.drop_table(table_name)

    def __repr__(self) -> str:
        """Représentation string du manager."""
        tables = self.list_tables()
        return f"LanceDBManager(path='{self.db_path}', tables={tables})"
