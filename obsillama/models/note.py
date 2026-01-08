"""
ObsIllama - Modèle de données Note

Ce module définit le modèle Pydantic pour représenter une note Obsidian.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator


class Note(BaseModel):
    """
    Modèle représentant une note Obsidian.

    Une note contient le contenu markdown, les métadonnées du frontmatter,
    les tags, les backlinks, et d'autres informations extraites.
    """

    # Identifiant unique
    id: str = Field(..., description="ID unique de la note (hash du path)")

    # Informations du fichier
    file_path: str = Field(..., description="Chemin absolu vers le fichier")
    file_name: str = Field(..., description="Nom du fichier (avec extension)")
    relative_path: str = Field(
        ..., description="Chemin relatif depuis la racine du vault"
    )

    # Métadonnées temporelles
    created_at: Optional[datetime] = Field(
        None, description="Date de création du fichier"
    )
    modified_at: Optional[datetime] = Field(
        None, description="Date de dernière modification"
    )
    scanned_at: datetime = Field(
        default_factory=datetime.now, description="Date du scan par ObsIllama"
    )

    # Contenu
    title: str = Field(..., description="Titre de la note (depuis frontmatter ou H1)")
    content: str = Field(default="", description="Contenu markdown sans frontmatter")
    raw_content: str = Field(
        default="", description="Contenu brut complet (avec frontmatter)"
    )

    # Frontmatter YAML
    frontmatter: Dict[str, Any] = Field(
        default_factory=dict, description="Métadonnées du frontmatter YAML"
    )

    # Tags
    tags: List[str] = Field(
        default_factory=list, description="Tags extraits (frontmatter + inline)"
    )
    frontmatter_tags: List[str] = Field(
        default_factory=list, description="Tags du frontmatter uniquement"
    )
    inline_tags: List[str] = Field(
        default_factory=list, description="Tags inline (#tag) dans le contenu"
    )

    # Liens et backlinks
    backlinks: List[str] = Field(
        default_factory=list, description="Liens internes [[note]] trouvés"
    )
    external_links: List[str] = Field(
        default_factory=list, description="Liens externes (URLs)"
    )

    # Statistiques
    word_count: int = Field(default=0, ge=0, description="Nombre de mots")
    char_count: int = Field(default=0, ge=0, description="Nombre de caractères")
    heading_count: int = Field(default=0, ge=0, description="Nombre de headings (#)")

    # Informations de catégorisation (ajoutées par ObsIllama)
    ai_categories: List[str] = Field(
        default_factory=list, description="Catégories assignées par l'IA"
    )
    ai_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Score de confiance de l'assignation"
    )
    ai_processed: bool = Field(
        default=False, description="Si la note a été traitée par ObsIllama"
    )
    ai_processed_date: Optional[datetime] = Field(
        None, description="Date du traitement IA"
    )
    ai_version: Optional[str] = Field(
        None, description="Version d'ObsIllama utilisée"
    )

    # Embedding vectoriel (ajouté plus tard)
    has_embedding: bool = Field(
        default=False, description="Si un embedding a été généré"
    )
    embedding_model: Optional[str] = Field(
        None, description="Modèle utilisé pour l'embedding"
    )
    embedding_date: Optional[datetime] = Field(
        None, description="Date de génération de l'embedding"
    )

    # Métadonnées supplémentaires
    folder: str = Field(default="", description="Dossier parent de la note")
    is_daily_note: bool = Field(default=False, description="Si c'est une daily note")
    language: Optional[str] = Field(None, description="Langue détectée (fr, en, etc.)")

    @field_validator("tags", "frontmatter_tags", "inline_tags")
    @classmethod
    def normalize_tags(cls, v: List[str]) -> List[str]:
        """Normalise les tags (lowercase, sans #)"""
        if not v:
            return []
        return [tag.lower().strip().lstrip("#") for tag in v]

    @field_validator("file_path", "relative_path")
    @classmethod
    def validate_paths(cls, v: str) -> str:
        """Valide que les chemins ne sont pas vides"""
        if not v or not v.strip():
            raise ValueError("Le chemin ne peut pas être vide")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Valide que le titre n'est pas vide"""
        if not v or not v.strip():
            raise ValueError("Le titre ne peut pas être vide")
        return v.strip()

    def get_all_tags(self) -> List[str]:
        """
        Retourne tous les tags (frontmatter + inline) dédupliqués.

        Returns:
            List[str]: Liste des tags uniques
        """
        all_tags = set(self.tags)
        all_tags.update(self.frontmatter_tags)
        all_tags.update(self.inline_tags)
        return sorted(list(all_tags))

    def has_tag(self, tag: str) -> bool:
        """
        Vérifie si la note possède un tag donné.

        Args:
            tag: Le tag à rechercher (case-insensitive)

        Returns:
            bool: True si le tag existe
        """
        normalized_tag = tag.lower().strip().lstrip("#")
        return normalized_tag in self.get_all_tags()

    def get_folder_hierarchy(self) -> List[str]:
        """
        Retourne la hiérarchie de dossiers.

        Returns:
            List[str]: Liste des dossiers parents (du plus haut au plus bas)

        Example:
            "Projects/Work/Notes.md" -> ["Projects", "Work"]
        """
        if not self.folder:
            return []
        return self.folder.split("/")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la note en dictionnaire.

        Returns:
            Dict[str, Any]: Représentation dictionnaire de la note
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """
        Crée une instance de Note depuis un dictionnaire.

        Args:
            data: Dictionnaire contenant les données de la note

        Returns:
            Note: Instance de Note validée
        """
        return cls(**data)

    def get_summary(self) -> str:
        """
        Retourne un résumé textuel de la note.

        Returns:
            str: Résumé de la note
        """
        summary_parts = [
            f"Note: {self.title}",
            f"Path: {self.relative_path}",
            f"Words: {self.word_count}",
        ]

        if self.tags:
            summary_parts.append(f"Tags: {', '.join(self.tags[:3])}")

        if self.ai_categories:
            summary_parts.append(f"Categories: {', '.join(self.ai_categories)}")

        return " | ".join(summary_parts)

    def __str__(self) -> str:
        """Représentation textuelle de la note"""
        return f"<Note: {self.title} ({self.file_name})>"

    def __repr__(self) -> str:
        """Représentation pour le debugging"""
        return f"Note(id='{self.id}', title='{self.title}', path='{self.relative_path}')"

    class Config:
        """Configuration Pydantic"""

        # Permet l'utilisation de dates datetime
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}

        # Permet la validation lors de l'assignation
        validate_assignment = True

        # Schéma JSON avec exemples
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "file_path": "/vault/Projects/My Note.md",
                "file_name": "My Note.md",
                "relative_path": "Projects/My Note.md",
                "title": "My Note",
                "content": "This is the note content",
                "tags": ["project", "work"],
                "word_count": 100,
                "ai_categories": ["Technology", "Projects"],
                "ai_confidence": 0.85,
            }
        }
