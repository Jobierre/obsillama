"""
ObsIllama - Modèle de données Category

Ce module définit le modèle Pydantic pour représenter une catégorie de notes.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ReviewStatus(str, Enum):
    """Statut de review d'une catégorie"""

    PENDING = "pending"  # En attente de review
    APPROVED = "approved"  # Approuvée par l'utilisateur
    REJECTED = "rejected"  # Rejetée par l'utilisateur
    MODIFIED = "modified"  # Modifiée par l'utilisateur


class Category(BaseModel):
    """
    Modèle représentant une catégorie de notes.

    Une catégorie regroupe des notes similaires identifiées par GraphRAG
    et l'analyse sémantique. Elle peut avoir des catégories parentes et enfants
    pour créer une hiérarchie taxonomique.
    """

    # Identifiant unique
    id: str = Field(..., description="ID unique de la catégorie")

    # Informations de base
    name: str = Field(..., description="Nom de la catégorie (lisible)")
    description: str = Field(
        default="", description="Description générée par le LLM"
    )
    tag_name: str = Field(
        ..., description="Nom du tag Obsidian (AI-Category-{name})"
    )

    # Hiérarchie
    parent_id: Optional[str] = Field(
        None, description="ID de la catégorie parente (si sous-catégorie)"
    )
    children_ids: List[str] = Field(
        default_factory=list, description="IDs des catégories enfants"
    )
    level: int = Field(
        default=0, ge=0, description="Niveau dans la hiérarchie (0 = racine)"
    )

    # Métadonnées sémantiques
    keywords: List[str] = Field(
        default_factory=list, description="Mots-clés caractéristiques"
    )
    representative_terms: List[str] = Field(
        default_factory=list,
        description="Termes les plus représentatifs de la catégorie",
    )

    # Statistiques
    note_count: int = Field(
        default=0, ge=0, description="Nombre de notes assignées"
    )
    avg_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confiance moyenne des assignations",
    )

    # Scores de qualité
    coherence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de cohérence de la catégorie",
    )
    distinctiveness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de distinction par rapport aux autres",
    )

    # Review et validation
    review_status: ReviewStatus = Field(
        default=ReviewStatus.PENDING, description="Statut de review utilisateur"
    )
    reviewed_by: Optional[str] = Field(
        None, description="Utilisateur qui a reviewé"
    )
    reviewed_at: Optional[datetime] = Field(
        None, description="Date de la review"
    )

    # Métadonnées de création
    created_at: datetime = Field(
        default_factory=datetime.now, description="Date de création"
    )
    created_by: str = Field(
        default="graphrag", description="Méthode de création (graphrag, manual, etc.)"
    )
    community_id: Optional[str] = Field(
        None, description="ID de la communauté GraphRAG source"
    )

    # Métadonnées de modification
    modified_at: Optional[datetime] = Field(
        None, description="Date de dernière modification"
    )
    version: int = Field(default=1, ge=1, description="Version de la catégorie")

    # Suggestions d'amélioration
    merge_suggestions: List[str] = Field(
        default_factory=list,
        description="IDs de catégories similaires à fusionner",
    )
    split_suggested: bool = Field(
        default=False, description="Si la catégorie devrait être divisée"
    )

    # Couleur et icône (pour visualisation)
    color: Optional[str] = Field(
        None, description="Couleur hex pour visualisation (#RRGGBB)"
    )
    icon: Optional[str] = Field(
        None, description="Icône emoji ou unicode"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Valide que le nom n'est pas vide"""
        if not v or not v.strip():
            raise ValueError("Le nom de la catégorie ne peut pas être vide")
        return v.strip()

    @field_validator("tag_name")
    @classmethod
    def validate_tag_name(cls, v: str) -> str:
        """Valide et normalise le nom du tag"""
        if not v or not v.strip():
            raise ValueError("Le nom du tag ne peut pas être vide")

        # Normaliser le tag (pas d'espaces, lowercase, etc.)
        tag = v.strip().replace(" ", "-").lower()

        # Vérifier qu'il commence par le préfixe (optionnel)
        # if not tag.startswith("ai-category-"):
        #     tag = f"ai-category-{tag}"

        return tag

    @field_validator("keywords", "representative_terms")
    @classmethod
    def normalize_terms(cls, v: List[str]) -> List[str]:
        """Normalise les termes (lowercase, déduplication)"""
        if not v:
            return []
        return list(set(term.lower().strip() for term in v if term.strip()))

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Valide le format de couleur hex"""
        if v is None:
            return None

        color = v.strip()
        if not color.startswith("#"):
            color = f"#{color}"

        if len(color) != 7:
            raise ValueError(f"Couleur invalide (doit être #RRGGBB): {v}")

        # Vérifier que ce sont des caractères hex valides
        try:
            int(color[1:], 16)
        except ValueError:
            raise ValueError(f"Couleur hex invalide: {v}")

        return color.upper()

    def is_root_category(self) -> bool:
        """
        Vérifie si c'est une catégorie racine (sans parent).

        Returns:
            bool: True si catégorie racine
        """
        return self.parent_id is None

    def is_subcategory(self) -> bool:
        """
        Vérifie si c'est une sous-catégorie (a un parent).

        Returns:
            bool: True si sous-catégorie
        """
        return self.parent_id is not None

    def has_children(self) -> bool:
        """
        Vérifie si la catégorie a des enfants.

        Returns:
            bool: True si a des enfants
        """
        return len(self.children_ids) > 0

    def is_approved(self) -> bool:
        """
        Vérifie si la catégorie est approuvée.

        Returns:
            bool: True si approuvée
        """
        return self.review_status == ReviewStatus.APPROVED

    def needs_review(self) -> bool:
        """
        Vérifie si la catégorie nécessite une review.

        Returns:
            bool: True si en attente de review
        """
        return self.review_status == ReviewStatus.PENDING

    def approve(self, reviewer: str = "user") -> None:
        """
        Approuve la catégorie.

        Args:
            reviewer: Nom de l'utilisateur qui approuve
        """
        self.review_status = ReviewStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now()

    def reject(self, reviewer: str = "user") -> None:
        """
        Rejette la catégorie.

        Args:
            reviewer: Nom de l'utilisateur qui rejette
        """
        self.review_status = ReviewStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now()

    def update_stats(self, note_count: int, avg_confidence: float) -> None:
        """
        Met à jour les statistiques de la catégorie.

        Args:
            note_count: Nouveau nombre de notes
            avg_confidence: Nouvelle confiance moyenne
        """
        self.note_count = note_count
        self.avg_confidence = avg_confidence
        self.modified_at = datetime.now()
        self.version += 1

    def add_merge_suggestion(self, category_id: str) -> None:
        """
        Ajoute une suggestion de fusion.

        Args:
            category_id: ID de la catégorie à fusionner
        """
        if category_id not in self.merge_suggestions:
            self.merge_suggestions.append(category_id)

    def get_full_path(self, categories: Dict[str, "Category"]) -> str:
        """
        Retourne le chemin complet de la catégorie dans la hiérarchie.

        Args:
            categories: Dictionnaire {id: Category} de toutes les catégories

        Returns:
            str: Chemin complet (ex: "Technology/Programming/Python")
        """
        path_parts = [self.name]
        current_id = self.parent_id

        while current_id:
            if current_id not in categories:
                break
            parent = categories[current_id]
            path_parts.insert(0, parent.name)
            current_id = parent.parent_id

        return "/".join(path_parts)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la catégorie en dictionnaire.

        Returns:
            Dict[str, Any]: Représentation dictionnaire
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        """
        Crée une instance de Category depuis un dictionnaire.

        Args:
            data: Dictionnaire contenant les données

        Returns:
            Category: Instance validée
        """
        return cls(**data)

    def __str__(self) -> str:
        """Représentation textuelle"""
        return f"<Category: {self.name} ({self.note_count} notes, {self.review_status})>"

    def __repr__(self) -> str:
        """Représentation pour le debugging"""
        return f"Category(id='{self.id}', name='{self.name}', notes={self.note_count})"

    class Config:
        """Configuration Pydantic"""

        # Validation lors de l'assignation
        validate_assignment = True

        # Encodage JSON
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            ReviewStatus: lambda v: v.value,
        }

        # Schéma JSON avec exemples
        json_schema_extra = {
            "example": {
                "id": "cat_tech_001",
                "name": "Technology",
                "description": "Notes about technology and software",
                "tag_name": "AI-Category-Technology",
                "parent_id": None,
                "children_ids": ["cat_tech_programming_001"],
                "level": 0,
                "keywords": ["software", "code", "tech"],
                "note_count": 42,
                "avg_confidence": 0.85,
                "review_status": "approved",
            }
        }
