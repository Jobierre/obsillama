"""
ObsIllama - Modèle de données Embedding

Ce module définit le modèle Pydantic pour représenter un embedding vectoriel.
"""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator
import numpy as np


class Embedding(BaseModel):
    """
    Modèle représentant un embedding vectoriel d'une note ou catégorie.

    Un embedding est une représentation vectorielle dense du contenu sémantique,
    permettant de calculer la similarité et effectuer des recherches sémantiques.
    """

    # Identifiant
    id: str = Field(..., description="ID unique de l'embedding")
    source_id: str = Field(
        ..., description="ID de la source (note_id ou category_id)"
    )
    source_type: Literal["note", "category"] = Field(
        ..., description="Type de source"
    )

    # Vecteur d'embedding
    vector: List[float] = Field(
        ..., description="Vecteur d'embedding (768 dimensions pour nomic-embed-text)"
    )

    # Métadonnées du modèle
    model_name: str = Field(
        default="nomic-embed-text", description="Nom du modèle d'embedding"
    )
    model_dimension: int = Field(
        default=768, ge=1, description="Dimension du vecteur"
    )

    # Métadonnées temporelles
    created_at: datetime = Field(
        default_factory=datetime.now, description="Date de création"
    )

    # Métadonnées de génération
    content_hash: str = Field(
        ..., description="Hash du contenu utilisé pour générer l'embedding"
    )
    content_length: int = Field(
        default=0, ge=0, description="Longueur du contenu source (caractères)"
    )
    truncated: bool = Field(
        default=False, description="Si le contenu a été tronqué"
    )

    # Métadonnées de qualité
    norm: Optional[float] = Field(
        None, ge=0.0, description="Norme L2 du vecteur (magnitude)"
    )
    is_normalized: bool = Field(
        default=False, description="Si le vecteur est normalisé"
    )

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Valide que le vecteur n'est pas vide et contient des nombres valides"""
        if not v:
            raise ValueError("Le vecteur ne peut pas être vide")

        # Vérifier que toutes les valeurs sont des nombres finis
        if not all(isinstance(x, (int, float)) and np.isfinite(x) for x in v):
            raise ValueError("Le vecteur contient des valeurs invalides (NaN ou Inf)")

        return v

    @field_validator("model_dimension")
    @classmethod
    def validate_dimension(cls, v: int, info) -> int:
        """Valide que la dimension correspond à la taille du vecteur"""
        # Note: cette validation sera faite après que 'vector' soit validé
        return v

    def model_post_init(self, __context) -> None:
        """Validation post-init pour vérifier la cohérence entre vector et dimension"""
        if len(self.vector) != self.model_dimension:
            raise ValueError(
                f"La dimension du vecteur ({len(self.vector)}) ne correspond pas "
                f"à model_dimension ({self.model_dimension})"
            )

        # Calculer la norme si pas déjà définie
        if self.norm is None:
            self.norm = float(np.linalg.norm(self.vector))

    def get_numpy_vector(self) -> np.ndarray:
        """
        Retourne le vecteur comme array NumPy.

        Returns:
            np.ndarray: Vecteur NumPy
        """
        return np.array(self.vector, dtype=np.float32)

    def normalize(self) -> "Embedding":
        """
        Normalise le vecteur (norme L2 = 1).

        Returns:
            Embedding: Nouvel embedding avec vecteur normalisé
        """
        if self.is_normalized:
            return self

        vec = self.get_numpy_vector()
        norm = np.linalg.norm(vec)

        if norm == 0:
            raise ValueError("Impossible de normaliser un vecteur nul")

        normalized_vec = vec / norm

        return Embedding(
            id=self.id,
            source_id=self.source_id,
            source_type=self.source_type,
            vector=normalized_vec.tolist(),
            model_name=self.model_name,
            model_dimension=self.model_dimension,
            created_at=self.created_at,
            content_hash=self.content_hash,
            content_length=self.content_length,
            truncated=self.truncated,
            norm=1.0,
            is_normalized=True,
        )

    def cosine_similarity(self, other: "Embedding") -> float:
        """
        Calcule la similarité cosinus avec un autre embedding.

        Args:
            other: Autre embedding

        Returns:
            float: Similarité cosinus (entre -1 et 1, généralement 0-1)

        Raises:
            ValueError: Si les dimensions ne correspondent pas
        """
        if self.model_dimension != other.model_dimension:
            raise ValueError(
                f"Dimensions incompatibles: {self.model_dimension} vs {other.model_dimension}"
            )

        vec1 = self.get_numpy_vector()
        vec2 = other.get_numpy_vector()

        # Normaliser les vecteurs
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Similarité cosinus = dot product / (norm1 * norm2)
        similarity = float(np.dot(vec1, vec2) / (norm1 * norm2))

        # Borner entre -1 et 1 (pour gérer les erreurs d'arrondi)
        return max(-1.0, min(1.0, similarity))

    def euclidean_distance(self, other: "Embedding") -> float:
        """
        Calcule la distance euclidienne avec un autre embedding.

        Args:
            other: Autre embedding

        Returns:
            float: Distance euclidienne

        Raises:
            ValueError: Si les dimensions ne correspondent pas
        """
        if self.model_dimension != other.model_dimension:
            raise ValueError(
                f"Dimensions incompatibles: {self.model_dimension} vs {other.model_dimension}"
            )

        vec1 = self.get_numpy_vector()
        vec2 = other.get_numpy_vector()

        return float(np.linalg.norm(vec1 - vec2))

    def dot_product(self, other: "Embedding") -> float:
        """
        Calcule le produit scalaire avec un autre embedding.

        Args:
            other: Autre embedding

        Returns:
            float: Produit scalaire

        Raises:
            ValueError: Si les dimensions ne correspondent pas
        """
        if self.model_dimension != other.model_dimension:
            raise ValueError(
                f"Dimensions incompatibles: {self.model_dimension} vs {other.model_dimension}"
            )

        vec1 = self.get_numpy_vector()
        vec2 = other.get_numpy_vector()

        return float(np.dot(vec1, vec2))

    def __str__(self) -> str:
        """Représentation textuelle"""
        return (
            f"<Embedding: {self.source_type}:{self.source_id} "
            f"({self.model_name}, dim={self.model_dimension})>"
        )

    def __repr__(self) -> str:
        """Représentation pour le debugging"""
        return (
            f"Embedding(id='{self.id}', source='{self.source_type}:{self.source_id}', "
            f"dim={self.model_dimension})"
        )

    class Config:
        """Configuration Pydantic"""

        # Validation lors de l'assignation
        validate_assignment = True

        # Encodage JSON
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            np.ndarray: lambda v: v.tolist(),
        }

        # Schéma JSON avec exemples
        json_schema_extra = {
            "example": {
                "id": "emb_note_001",
                "source_id": "note_abc123",
                "source_type": "note",
                "vector": [0.1, 0.2, 0.3],  # Simplifié, normalement 768 dimensions
                "model_name": "nomic-embed-text",
                "model_dimension": 768,
                "content_hash": "sha256_hash_here",
                "content_length": 1500,
                "norm": 1.0,
                "is_normalized": True,
            }
        }
