"""
ObsIllama - Modèles de données GraphRAG

Ce module définit les modèles Pydantic pour GraphRAG:
- GraphEntity: Entité extraite d'une note
- GraphRelationship: Relation entre deux entités
- GraphCommunity: Communauté détectée dans le graphe
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================


class EntityType(str, Enum):
    """Types d'entités extraites"""

    TECHNOLOGY = "technology"  # Technologies (Python, Docker, etc.)
    CONCEPT = "concept"  # Concepts abstraits
    TOOL = "tool"  # Outils et logiciels
    PERSON = "person"  # Personnes et auteurs
    ORGANIZATION = "organization"  # Organisations et entreprises
    PROJECT = "project"  # Projets
    METHODOLOGY = "methodology"  # Méthodologies et frameworks
    OTHER = "other"  # Autre


class RelationshipType(str, Enum):
    """Types de relations entre entités"""

    USES = "uses"  # A utilise B
    PART_OF = "part_of"  # A fait partie de B
    RELATED_TO = "related_to"  # A est lié à B
    IMPLEMENTS = "implements"  # A implémente B
    DEPENDS_ON = "depends_on"  # A dépend de B
    SIMILAR_TO = "similar_to"  # A est similaire à B
    CREATED_BY = "created_by"  # A est créé par B
    WORKS_WITH = "works_with"  # A travaille avec B
    OTHER = "other"  # Autre relation


# =============================================================================
# GraphEntity - Entité extraite
# =============================================================================


class GraphEntity(BaseModel):
    """
    Modèle représentant une entité extraite du graphe de connaissances.

    Une entité est un concept, une personne, une technologie, etc.
    identifié dans les notes via GraphRAG.
    """

    # Identifiant
    id: str = Field(..., description="ID unique de l'entité")

    # Informations de base
    name: str = Field(..., description="Nom de l'entité")
    type: EntityType = Field(..., description="Type d'entité")
    description: str = Field(default="", description="Description de l'entité")

    # Synonymes et variations
    aliases: List[str] = Field(
        default_factory=list, description="Noms alternatifs et synonymes"
    )

    # Sources
    source_note_ids: List[str] = Field(
        default_factory=list, description="IDs des notes où l'entité apparaît"
    )
    mention_count: int = Field(
        default=0, ge=0, description="Nombre de mentions totales"
    )

    # Contexte
    context_snippets: List[str] = Field(
        default_factory=list,
        description="Extraits de contexte où l'entité est mentionnée",
    )

    # Importance
    importance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score d'importance de l'entité",
    )
    centrality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Centralité dans le graphe",
    )

    # Communauté
    community_id: Optional[str] = Field(
        None, description="ID de la communauté à laquelle l'entité appartient"
    )

    # Métadonnées
    created_at: datetime = Field(
        default_factory=datetime.now, description="Date de création"
    )
    extracted_by: str = Field(
        default="graphrag", description="Méthode d'extraction"
    )

    # Propriétés additionnelles (flexibles)
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Propriétés supplémentaires"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Valide que le nom n'est pas vide"""
        if not v or not v.strip():
            raise ValueError("Le nom de l'entité ne peut pas être vide")
        return v.strip()

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, v: List[str]) -> List[str]:
        """Normalise les aliases"""
        if not v:
            return []
        return list(set(alias.strip() for alias in v if alias.strip()))

    def add_mention(self, note_id: str, context: Optional[str] = None) -> None:
        """
        Ajoute une mention de l'entité dans une note.

        Args:
            note_id: ID de la note
            context: Contexte optionnel de la mention
        """
        if note_id not in self.source_note_ids:
            self.source_note_ids.append(note_id)

        self.mention_count += 1

        if context and len(self.context_snippets) < 10:  # Limiter à 10 contextes
            self.context_snippets.append(context)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEntity":
        """Crée depuis un dictionnaire"""
        return cls(**data)

    def __str__(self) -> str:
        return f"<GraphEntity: {self.name} ({self.type}, {self.mention_count} mentions)>"

    def __repr__(self) -> str:
        return f"GraphEntity(id='{self.id}', name='{self.name}', type='{self.type}')"

    class Config:
        """Configuration Pydantic"""
        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# =============================================================================
# GraphRelationship - Relation entre entités
# =============================================================================


class GraphRelationship(BaseModel):
    """
    Modèle représentant une relation entre deux entités.

    Une relation connecte deux entités du graphe de connaissances.
    """

    # Identifiant
    id: str = Field(..., description="ID unique de la relation")

    # Entités connectées
    source_entity_id: str = Field(..., description="ID de l'entité source")
    target_entity_id: str = Field(..., description="ID de l'entité cible")

    # Type de relation
    relationship_type: RelationshipType = Field(..., description="Type de relation")
    description: str = Field(default="", description="Description de la relation")

    # Poids et confiance
    weight: float = Field(
        default=1.0, ge=0.0, description="Poids de la relation"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confiance dans la relation"
    )

    # Sources
    source_note_ids: List[str] = Field(
        default_factory=list, description="Notes où la relation est observée"
    )
    evidence_count: int = Field(
        default=0, ge=0, description="Nombre d'évidences de la relation"
    )

    # Contexte
    context_snippets: List[str] = Field(
        default_factory=list,
        description="Extraits montrant la relation",
    )

    # Métadonnées
    created_at: datetime = Field(
        default_factory=datetime.now, description="Date de création"
    )
    extracted_by: str = Field(
        default="graphrag", description="Méthode d'extraction"
    )

    # Propriétés additionnelles
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Propriétés supplémentaires"
    )

    def add_evidence(self, note_id: str, context: Optional[str] = None) -> None:
        """
        Ajoute une évidence de la relation.

        Args:
            note_id: ID de la note
            context: Contexte optionnel
        """
        if note_id not in self.source_note_ids:
            self.source_note_ids.append(note_id)

        self.evidence_count += 1

        if context and len(self.context_snippets) < 5:  # Limiter à 5 contextes
            self.context_snippets.append(context)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphRelationship":
        """Crée depuis un dictionnaire"""
        return cls(**data)

    def __str__(self) -> str:
        return (
            f"<GraphRelationship: {self.source_entity_id} -{self.relationship_type}-> "
            f"{self.target_entity_id}>"
        )

    def __repr__(self) -> str:
        return (
            f"GraphRelationship(id='{self.id}', "
            f"source='{self.source_entity_id}', target='{self.target_entity_id}')"
        )

    class Config:
        """Configuration Pydantic"""
        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# =============================================================================
# GraphCommunity - Communauté détectée
# =============================================================================


class GraphCommunity(BaseModel):
    """
    Modèle représentant une communauté dans le graphe de connaissances.

    Une communauté est un groupe d'entités fortement connectées,
    détecté par l'algorithme de Leiden ou Louvain.
    """

    # Identifiant
    id: str = Field(..., description="ID unique de la communauté")

    # Métadonnées de base
    name: str = Field(default="", description="Nom de la communauté (généré)")
    description: str = Field(
        default="", description="Description générée par le LLM"
    )

    # Membres
    entity_ids: List[str] = Field(
        default_factory=list, description="IDs des entités membres"
    )
    entity_count: int = Field(
        default=0, ge=0, description="Nombre d'entités dans la communauté"
    )

    # Structure
    internal_edges: int = Field(
        default=0, ge=0, description="Nombre de liens internes"
    )
    external_edges: int = Field(
        default=0, ge=0, description="Nombre de liens externes"
    )

    # Scores de qualité
    coherence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de cohérence interne",
    )
    modularity: float = Field(
        default=0.0, description="Modularité de la communauté"
    )
    density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Densité des connexions internes",
    )

    # Hiérarchie
    parent_community_id: Optional[str] = Field(
        None, description="ID de la communauté parente (si hiérarchique)"
    )
    level: int = Field(
        default=0, ge=0, description="Niveau dans la hiérarchie"
    )

    # Représentativité
    top_entities: List[str] = Field(
        default_factory=list,
        description="IDs des entités les plus représentatives",
    )
    keywords: List[str] = Field(
        default_factory=list, description="Mots-clés caractéristiques"
    )

    # Notes associées
    associated_note_ids: List[str] = Field(
        default_factory=list, description="Notes associées à la communauté"
    )

    # Métadonnées de détection
    detected_at: datetime = Field(
        default_factory=datetime.now, description="Date de détection"
    )
    algorithm: str = Field(
        default="leiden", description="Algorithme de détection (leiden, louvain)"
    )
    resolution: float = Field(
        default=1.0, description="Résolution utilisée pour la détection"
    )

    # Mapping vers catégorie
    mapped_category_id: Optional[str] = Field(
        None, description="ID de la catégorie générée depuis cette communauté"
    )

    @field_validator("entity_ids")
    @classmethod
    def deduplicate_entities(cls, v: List[str]) -> List[str]:
        """Déduplique les IDs d'entités"""
        return list(set(v)) if v else []

    def model_post_init(self, __context) -> None:
        """Post-init pour synchroniser entity_count"""
        self.entity_count = len(self.entity_ids)

    def add_entity(self, entity_id: str) -> None:
        """
        Ajoute une entité à la communauté.

        Args:
            entity_id: ID de l'entité
        """
        if entity_id not in self.entity_ids:
            self.entity_ids.append(entity_id)
            self.entity_count = len(self.entity_ids)

    def remove_entity(self, entity_id: str) -> None:
        """
        Retire une entité de la communauté.

        Args:
            entity_id: ID de l'entité
        """
        if entity_id in self.entity_ids:
            self.entity_ids.remove(entity_id)
            self.entity_count = len(self.entity_ids)

    def calculate_density(self) -> float:
        """
        Calcule la densité de la communauté.

        Returns:
            float: Densité (ratio liens internes / liens possibles)
        """
        if self.entity_count <= 1:
            return 0.0

        max_edges = self.entity_count * (self.entity_count - 1) / 2
        if max_edges == 0:
            return 0.0

        density = self.internal_edges / max_edges
        self.density = min(1.0, density)  # Borner à 1.0
        return self.density

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphCommunity":
        """Crée depuis un dictionnaire"""
        return cls(**data)

    def __str__(self) -> str:
        return (
            f"<GraphCommunity: {self.name or self.id} "
            f"({self.entity_count} entities, coherence={self.coherence_score:.2f})>"
        )

    def __repr__(self) -> str:
        return (
            f"GraphCommunity(id='{self.id}', entities={self.entity_count}, "
            f"coherence={self.coherence_score:.2f})"
        )

    class Config:
        """Configuration Pydantic"""
        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
