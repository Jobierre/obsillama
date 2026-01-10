"""
ObsIllama - Graph Store

Ce module gère le stockage et la récupération du graphe de connaissances GraphRAG.
Il utilise LanceDB pour les entités et communautés, et JSON pour les relations.
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from obsillama.storage.lancedb_manager import (
    LanceDBManager,
    EntityRecord,
    CommunityRecord,
)
from obsillama.models.graph_entity import (
    GraphEntity,
    GraphRelationship,
    GraphCommunity,
    EntityType,
    RelationshipType,
)
from obsillama.config.settings import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# GraphStore
# =============================================================================


class GraphStore:
    """
    Gestionnaire de stockage pour le graphe de connaissances GraphRAG.

    Ce store gère :
    - Entités : stockées dans LanceDB avec embeddings
    - Relations : stockées en JSON (pas besoin d'embeddings)
    - Communautés : stockées dans LanceDB avec embeddings

    Attributes:
        db_manager: Manager LanceDB
        relationships_file: Chemin du fichier JSON des relations
    """

    def __init__(
        self,
        db_manager: Optional[LanceDBManager] = None,
        relationships_file: Optional[str] = None,
    ):
        """
        Initialise le GraphStore.

        Args:
            db_manager: Manager LanceDB (créé si None)
            relationships_file: Chemin du fichier JSON pour les relations
        """
        self.db_manager = db_manager or LanceDBManager()

        # Fichier pour stocker les relations
        if relationships_file:
            self.relationships_file = Path(relationships_file)
        else:
            # Stocker dans data/categories/graph_relationships.json
            self.relationships_file = Path("data/categories/graph_relationships.json")

        # Créer le dossier parent si nécessaire
        self.relationships_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"GraphStore initialisé: {self.relationships_file}")

    # =========================================================================
    # Sauvegarde
    # =========================================================================

    def save_entities(
        self, entities: List[GraphEntity], embeddings: List[List[float]]
    ) -> None:
        """
        Sauvegarde les entités dans LanceDB.

        Args:
            entities: Liste des entités GraphRAG
            embeddings: Embeddings des entités (descriptions)

        Raises:
            ValueError: Si le nombre d'entités != nombre d'embeddings
        """
        if len(entities) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(entities)} entités vs {len(embeddings)} embeddings"
            )

        logger.info(f"Sauvegarde de {len(entities)} entités dans LanceDB")

        try:
            # Ouvrir ou créer la table
            try:
                table = self.db_manager.db.open_table("entities")
            except Exception:
                logger.info("Table 'entities' n'existe pas, création...")
                self.db_manager.create_entities_table()
                table = self.db_manager.db.open_table("entities")

            # Convertir en EntityRecord
            records = []
            for entity, embedding in zip(entities, embeddings):
                record = EntityRecord(
                    id=entity.id,
                    name=entity.name,
                    entity_type=entity.type.value,
                    description=entity.description,
                    note_ids=entity.source_note_ids,
                    frequency=entity.mention_count,
                    importance_score=entity.importance_score,
                    created_at=entity.created_at.isoformat(),
                    vector=embedding,
                )
                records.append(record)

            # Insérer dans LanceDB
            table.add(records)

            logger.info(f"{len(records)} entités sauvegardées avec succès")

        except Exception as e:
            logger.error(f"Erreur sauvegarde entités : {e}")
            raise

    def save_relationships(self, relationships: List[GraphRelationship]) -> None:
        """
        Sauvegarde les relations dans un fichier JSON.

        Les relations n'ont pas besoin d'embeddings, donc on les stocke en JSON
        pour simplifier et éviter le coût de génération d'embeddings inutiles.

        Args:
            relationships: Liste des relations GraphRAG
        """
        logger.info(
            f"Sauvegarde de {len(relationships)} relations dans {self.relationships_file}"
        )

        try:
            # Convertir en dictionnaires (mode='json' pour convertir datetime en ISO)
            relationships_data = [rel.model_dump(mode='json') for rel in relationships]

            # Sauvegarder en JSON
            with open(self.relationships_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "relationships": relationships_data,
                        "count": len(relationships_data),
                        "saved_at": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(f"{len(relationships)} relations sauvegardées avec succès")

        except Exception as e:
            logger.error(f"Erreur sauvegarde relations : {e}")
            raise

    def save_communities(
        self, communities: List[GraphCommunity], embeddings: List[List[float]]
    ) -> None:
        """
        Sauvegarde les communautés dans LanceDB.

        Args:
            communities: Liste des communautés GraphRAG
            embeddings: Embeddings des communautés (descriptions)

        Raises:
            ValueError: Si le nombre de communautés != nombre d'embeddings
        """
        if len(communities) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(communities)} communautés vs {len(embeddings)} embeddings"
            )

        logger.info(f"Sauvegarde de {len(communities)} communautés dans LanceDB")

        try:
            # Ouvrir ou créer la table
            try:
                table = self.db_manager.db.open_table("communities")
            except Exception:
                logger.info("Table 'communities' n'existe pas, création...")
                self.db_manager.create_communities_table()
                table = self.db_manager.db.open_table("communities")

            # Convertir en CommunityRecord
            records = []
            for community, embedding in zip(communities, embeddings):
                # Récupérer les note_ids depuis les entités
                note_ids = list(community.associated_note_ids)

                record = CommunityRecord(
                    id=community.id,
                    name=community.name,
                    description=community.description,
                    summary=community.description,  # Utiliser description comme summary
                    entity_ids=community.entity_ids,
                    note_ids=note_ids,
                    size=community.entity_count,
                    density=community.density,
                    created_at=community.detected_at.isoformat(),
                    algorithm=community.algorithm,
                    vector=embedding,
                )
                records.append(record)

            # Insérer dans LanceDB
            table.add(records)

            logger.info(f"{len(records)} communautés sauvegardées avec succès")

        except Exception as e:
            logger.error(f"Erreur sauvegarde communautés : {e}")
            raise

    def save_graph(
        self,
        entities: List[GraphEntity],
        relationships: List[GraphRelationship],
        communities: List[GraphCommunity],
        entity_embeddings: List[List[float]],
        community_embeddings: List[List[float]],
    ) -> None:
        """
        Sauvegarde le graphe complet (entités, relations, communautés).

        Args:
            entities: Liste des entités
            relationships: Liste des relations
            communities: Liste des communautés
            entity_embeddings: Embeddings des entités
            community_embeddings: Embeddings des communautés
        """
        logger.info(
            f"Sauvegarde du graphe complet : "
            f"{len(entities)} entités, "
            f"{len(relationships)} relations, "
            f"{len(communities)} communautés"
        )

        # Sauvegarder chaque composant
        self.save_entities(entities, entity_embeddings)
        self.save_relationships(relationships)
        self.save_communities(communities, community_embeddings)

        logger.info("Graphe complet sauvegardé avec succès")

    # =========================================================================
    # Chargement
    # =========================================================================

    def load_entities(self) -> List[GraphEntity]:
        """
        Charge toutes les entités depuis LanceDB.

        Returns:
            Liste des entités GraphRAG

        Raises:
            ValueError: Si la table n'existe pas
        """
        logger.info("Chargement des entités depuis LanceDB")

        try:
            # Ouvrir la table
            table = self.db_manager.db.open_table("entities")

            # Récupérer toutes les entités
            results = table.to_pandas()

            # Convertir en objets GraphEntity
            entities = []
            for _, row in results.iterrows():
                entity = GraphEntity(
                    id=row["id"],
                    name=row["name"],
                    type=EntityType(row["entity_type"]),
                    description=row["description"],
                    source_note_ids=row["note_ids"],
                    mention_count=row["frequency"],
                    importance_score=row["importance_score"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                entities.append(entity)

            logger.info(f"{len(entities)} entités chargées")
            return entities

        except Exception as e:
            logger.error(f"Erreur chargement entités : {e}")
            raise ValueError(f"Impossible de charger les entités : {e}")

    def load_relationships(self) -> List[GraphRelationship]:
        """
        Charge toutes les relations depuis le fichier JSON.

        Returns:
            Liste des relations GraphRAG

        Raises:
            ValueError: Si le fichier n'existe pas
        """
        logger.info(f"Chargement des relations depuis {self.relationships_file}")

        if not self.relationships_file.exists():
            logger.warning("Fichier de relations n'existe pas")
            return []

        try:
            # Charger le JSON
            with open(self.relationships_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            relationships_data = data.get("relationships", [])

            # Convertir en objets GraphRelationship
            relationships = []
            for rel_data in relationships_data:
                # Convertir les dates
                if isinstance(rel_data.get("created_at"), str):
                    rel_data["created_at"] = datetime.fromisoformat(
                        rel_data["created_at"]
                    )

                # Convertir les enums
                if isinstance(rel_data.get("relationship_type"), str):
                    rel_data["relationship_type"] = RelationshipType(
                        rel_data["relationship_type"]
                    )

                relationship = GraphRelationship.from_dict(rel_data)
                relationships.append(relationship)

            logger.info(f"{len(relationships)} relations chargées")
            return relationships

        except Exception as e:
            logger.error(f"Erreur chargement relations : {e}")
            raise ValueError(f"Impossible de charger les relations : {e}")

    def load_communities(self) -> List[GraphCommunity]:
        """
        Charge toutes les communautés depuis LanceDB.

        Returns:
            Liste des communautés GraphRAG

        Raises:
            ValueError: Si la table n'existe pas
        """
        logger.info("Chargement des communautés depuis LanceDB")

        try:
            # Ouvrir la table
            table = self.db_manager.db.open_table("communities")

            # Récupérer toutes les communautés
            results = table.to_pandas()

            # Convertir en objets GraphCommunity
            communities = []
            for _, row in results.iterrows():
                community = GraphCommunity(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    entity_ids=row["entity_ids"],
                    entity_count=row["size"],
                    density=row["density"],
                    detected_at=datetime.fromisoformat(row["created_at"]),
                    algorithm=row["algorithm"],
                    associated_note_ids=row["note_ids"],
                )
                communities.append(community)

            logger.info(f"{len(communities)} communautés chargées")
            return communities

        except Exception as e:
            logger.error(f"Erreur chargement communautés : {e}")
            raise ValueError(f"Impossible de charger les communautés : {e}")

    def load_graph(
        self,
    ) -> Tuple[List[GraphEntity], List[GraphRelationship], List[GraphCommunity]]:
        """
        Charge le graphe complet depuis le stockage.

        Returns:
            Tuple (entités, relations, communautés)
        """
        logger.info("Chargement du graphe complet")

        entities = self.load_entities()
        relationships = self.load_relationships()
        communities = self.load_communities()

        logger.info(
            f"Graphe chargé : "
            f"{len(entities)} entités, "
            f"{len(relationships)} relations, "
            f"{len(communities)} communautés"
        )

        return entities, relationships, communities

    # =========================================================================
    # Utilitaires
    # =========================================================================

    def get_entity_by_id(self, entity_id: str) -> Optional[GraphEntity]:
        """
        Récupère une entité par son ID.

        Args:
            entity_id: ID de l'entité

        Returns:
            Entité ou None si non trouvée
        """
        try:
            table = self.db_manager.db.open_table("entities")
            results = table.search().where(f"id = '{entity_id}'").to_pandas()

            if len(results) == 0:
                return None

            row = results.iloc[0]
            return GraphEntity(
                id=row["id"],
                name=row["name"],
                type=EntityType(row["entity_type"]),
                description=row["description"],
                source_note_ids=row["note_ids"],
                mention_count=row["frequency"],
                importance_score=row["importance_score"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

        except Exception as e:
            logger.error(f"Erreur récupération entité {entity_id} : {e}")
            return None

    def get_community_by_id(self, community_id: str) -> Optional[GraphCommunity]:
        """
        Récupère une communauté par son ID.

        Args:
            community_id: ID de la communauté

        Returns:
            Communauté ou None si non trouvée
        """
        try:
            table = self.db_manager.db.open_table("communities")
            results = table.search().where(f"id = '{community_id}'").to_pandas()

            if len(results) == 0:
                return None

            row = results.iloc[0]
            return GraphCommunity(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                entity_ids=row["entity_ids"],
                entity_count=row["size"],
                density=row["density"],
                detected_at=datetime.fromisoformat(row["created_at"]),
                algorithm=row["algorithm"],
                associated_note_ids=row["note_ids"],
            )

        except Exception as e:
            logger.error(f"Erreur récupération communauté {community_id} : {e}")
            return None

    def clear_graph(self) -> None:
        """
        Supprime toutes les données du graphe (entités, relations, communautés).

        ATTENTION : Cette opération est irréversible !
        """
        logger.warning("Suppression de toutes les données du graphe")

        try:
            # Supprimer les tables LanceDB
            self.db_manager.db.drop_table("entities")
            self.db_manager.db.drop_table("communities")

            # Supprimer le fichier des relations
            if self.relationships_file.exists():
                self.relationships_file.unlink()

            logger.info("Graphe complètement supprimé")

        except Exception as e:
            logger.error(f"Erreur suppression graphe : {e}")
            raise
