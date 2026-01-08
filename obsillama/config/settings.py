"""
ObsIllama - Configuration Settings

Ce module gère le chargement et la validation de la configuration depuis config.yaml.
Il utilise Pydantic pour valider les types et les contraintes.
"""

import os
from pathlib import Path
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator
from ruamel.yaml import YAML


# ============================================================================
# Modèles Pydantic pour chaque section de configuration
# ============================================================================


class VaultConfig(BaseModel):
    """Configuration du vault Obsidian"""

    path: str = Field(..., description="Chemin absolu vers le vault Obsidian")
    backup_path: str = Field(
        default=".obsillama_backups", description="Dossier pour les backups"
    )
    exclude_folders: List[str] = Field(
        default_factory=lambda: [".obsidian", ".trash", "Templates"],
        description="Dossiers à exclure du scan",
    )

    @field_validator("path")
    @classmethod
    def validate_vault_path(cls, v: str) -> str:
        """Valide que le chemin du vault existe"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Le chemin du vault n'existe pas: {v}")
        if not path.is_dir():
            raise ValueError(f"Le chemin du vault n'est pas un dossier: {v}")
        return str(path.absolute())


class OllamaModelsConfig(BaseModel):
    """Configuration des modèles Ollama"""

    generation: str = Field(default="mistral", description="Modèle pour la génération")
    embedding: str = Field(
        default="nomic-embed-text", description="Modèle pour les embeddings"
    )


class OllamaParamsConfig(BaseModel):
    """Paramètres de génération Ollama"""

    temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="Température de génération"
    )
    max_tokens: int = Field(
        default=2000, gt=0, le=8192, description="Nombre max de tokens"
    )
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")


class OllamaConfig(BaseModel):
    """Configuration Ollama"""

    base_url: str = Field(
        default="http://localhost:11434", description="URL de base de l'API Ollama"
    )
    models: OllamaModelsConfig = Field(default_factory=OllamaModelsConfig)
    params: OllamaParamsConfig = Field(default_factory=OllamaParamsConfig)


class GraphRAGConfig(BaseModel):
    """Configuration GraphRAG"""

    community_algorithm: Literal["leiden", "louvain"] = Field(
        default="leiden", description="Algorithme de détection de communautés"
    )
    resolution: float = Field(
        default=1.0, gt=0.0, description="Résolution du clustering"
    )
    min_community_size: int = Field(
        default=3, ge=1, description="Taille minimale d'une communauté"
    )
    entity_types: List[str] = Field(
        default_factory=lambda: [
            "technology",
            "concept",
            "tool",
            "person",
            "organization",
            "project",
            "methodology",
        ],
        description="Types d'entités à extraire",
    )


class CategorizationThresholdsConfig(BaseModel):
    """Seuils de catégorisation"""

    assignment_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Seuil minimum pour assigner une note",
    )
    merge_similarity: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Seuil pour fusion de catégories"
    )
    subcategory_threshold: int = Field(
        default=20, ge=1, description="Nombre de notes pour créer une sous-catégorie"
    )


class CategorizationConfig(BaseModel):
    """Configuration de la catégorisation"""

    target_count: int = Field(
        default=20, ge=1, le=100, description="Nombre de catégories cibles"
    )
    min_notes_per_category: int = Field(
        default=5, ge=1, description="Nombre minimum de notes par catégorie"
    )
    thresholds: CategorizationThresholdsConfig = Field(
        default_factory=CategorizationThresholdsConfig
    )
    tag_prefix: str = Field(
        default="AI-Category-", description="Préfixe pour les tags générés"
    )
    language: str = Field(default="fr", description="Langue des prompts")


class IncrementalConfig(BaseModel):
    """Configuration du mode incrémental"""

    enabled: bool = Field(default=True, description="Activer le tracking")
    check_interval_days: int = Field(
        default=7, ge=1, description="Fréquence de vérification (jours)"
    )
    auto_ameliorate: bool = Field(
        default=False, description="Auto-amélioration automatique"
    )
    recluster_threshold: int = Field(
        default=100, ge=1, description="Seuil pour re-clustering complet"
    )


class FrontmatterConfig(BaseModel):
    """Configuration du frontmatter writer"""

    preserve_structure: bool = Field(
        default=True, description="Préserver la structure YAML"
    )
    preserve_comments: bool = Field(
        default=True, description="Préserver les commentaires YAML"
    )
    fields_to_add: List[str] = Field(
        default_factory=lambda: [
            "ai_categories",
            "ai_confidence",
            "ai_processed_date",
            "ai_version",
        ],
        description="Champs à ajouter",
    )
    backup_before_write: bool = Field(
        default=True, description="Créer un backup avant modification"
    )
    dry_run_default: bool = Field(
        default=False, description="Mode dry-run par défaut"
    )


class LanceDBIndexParamsConfig(BaseModel):
    """Paramètres de l'index LanceDB"""

    num_partitions: int = Field(
        default=32, ge=1, description="Nombre de partitions pour IVF"
    )
    num_sub_vectors: int = Field(
        default=16, ge=1, description="Sous-vecteurs pour PQ"
    )


class LanceDBConfig(BaseModel):
    """Configuration LanceDB"""

    path: str = Field(default="data/lancedb", description="Chemin vers la BDD")
    index_type: Literal["IVF_PQ", "HNSW", "FLAT"] = Field(
        default="IVF_PQ", description="Type d'index vectoriel"
    )
    index_params: LanceDBIndexParamsConfig = Field(
        default_factory=LanceDBIndexParamsConfig
    )
    embedding_dim: int = Field(
        default=768, ge=1, description="Dimension des embeddings"
    )


class ProcessingSamplingConfig(BaseModel):
    """Configuration de l'échantillonnage"""

    strategy: Literal["random", "stratified", "all"] = Field(
        default="stratified", description="Stratégie d'échantillonnage"
    )
    percentage: int = Field(
        default=15, ge=1, le=100, description="Pourcentage d'échantillonnage"
    )


class ProcessingConfig(BaseModel):
    """Configuration du traitement parallèle"""

    num_workers: int = Field(
        default=4, ge=1, le=32, description="Nombre de workers parallèles"
    )
    embedding_batch_size: int = Field(
        default=32, ge=1, le=128, description="Taille des batchs pour embeddings"
    )
    note_batch_size: int = Field(
        default=50, ge=1, le=500, description="Taille des batchs pour notes"
    )
    sampling: ProcessingSamplingConfig = Field(default_factory=ProcessingSamplingConfig)


class LoggingRotationConfig(BaseModel):
    """Configuration de la rotation des logs"""

    max_size_mb: int = Field(default=10, ge=1, description="Taille max du fichier (MB)")
    backup_count: int = Field(
        default=5, ge=1, description="Nombre de fichiers à conserver"
    )


class LoggingConfig(BaseModel):
    """Configuration du logging"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Niveau de log"
    )
    file: str = Field(default="logs/obsillama.log", description="Fichier de log")
    rotation: LoggingRotationConfig = Field(default_factory=LoggingRotationConfig)
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Format des logs",
    )
    console: bool = Field(default=True, description="Afficher dans la console")


class MetadataConfig(BaseModel):
    """Métadonnées de configuration"""

    config_version: str = Field(default="0.1.0", description="Version du schéma")
    created_at: str = Field(
        default="2026-01-08", description="Date de création du config"
    )


# ============================================================================
# Modèle principal de configuration
# ============================================================================


class Settings(BaseModel):
    """Configuration complète d'ObsIllama"""

    vault: VaultConfig
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    graphrag: GraphRAGConfig = Field(default_factory=GraphRAGConfig)
    categorization: CategorizationConfig = Field(default_factory=CategorizationConfig)
    incremental: IncrementalConfig = Field(default_factory=IncrementalConfig)
    frontmatter: FrontmatterConfig = Field(default_factory=FrontmatterConfig)
    lancedb: LanceDBConfig = Field(default_factory=LanceDBConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "Settings":
        """
        Charge la configuration depuis un fichier YAML.

        Args:
            yaml_path: Chemin vers le fichier config.yaml

        Returns:
            Settings: Instance de configuration validée

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si la configuration est invalide
        """
        yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable: {yaml_path}")

        # Charger le YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False

        with open(yaml_path, "r", encoding="utf-8") as f:
            config_dict = yaml.load(f)

        # Créer et valider la configuration
        try:
            settings = cls(**config_dict)
            return settings
        except Exception as e:
            raise ValueError(f"Configuration invalide: {e}") from e

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Charge la configuration depuis les variables d'environnement.

        Cherche la variable OBSILLAMA_CONFIG_PATH, sinon utilise le chemin par défaut.

        Returns:
            Settings: Instance de configuration validée
        """
        config_path = os.environ.get("OBSILLAMA_CONFIG_PATH", "config/config.yaml")
        return cls.from_yaml(config_path)


# ============================================================================
# Instance globale de configuration
# ============================================================================

# Cette variable sera initialisée lors du premier appel à get_settings()
_settings: Optional[Settings] = None


def get_settings(config_path: Optional[str | Path] = None) -> Settings:
    """
    Récupère l'instance globale de configuration.

    Si la configuration n'a pas encore été chargée, elle est chargée depuis
    le fichier spécifié ou depuis le chemin par défaut.

    Args:
        config_path: Chemin optionnel vers le fichier config.yaml

    Returns:
        Settings: Instance de configuration
    """
    global _settings

    if _settings is None:
        if config_path:
            _settings = Settings.from_yaml(config_path)
        else:
            _settings = Settings.from_env()

    return _settings


def reload_settings(config_path: Optional[str | Path] = None) -> Settings:
    """
    Recharge la configuration depuis le fichier.

    Utile pour appliquer des changements de configuration sans redémarrer l'application.

    Args:
        config_path: Chemin optionnel vers le fichier config.yaml

    Returns:
        Settings: Nouvelle instance de configuration
    """
    global _settings
    _settings = None
    return get_settings(config_path)
