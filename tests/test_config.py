"""
Tests pour la configuration ObsIllama

Ce module teste le chargement et la validation de config.yaml
"""

import sys
from pathlib import Path

import pytest

# Ajouter le dossier parent au path pour importer obsillama
sys.path.insert(0, str(Path(__file__).parent.parent))

from obsillama.config.settings import Settings, get_settings, reload_settings


# =============================================================================
# Fixtures pytest
# =============================================================================


@pytest.fixture
def config_path():
    """Retourne le chemin vers le fichier de configuration"""
    return "config/config.yaml"


@pytest.fixture
def settings(config_path):
    """Charge et retourne la configuration"""
    return Settings.from_yaml(config_path)


# =============================================================================
# Tests de chargement
# =============================================================================


def test_config_file_exists(config_path):
    """Test que le fichier de configuration existe"""
    assert Path(config_path).exists(), f"Fichier de configuration introuvable: {config_path}"


def test_config_loads_successfully(config_path):
    """Test que la configuration se charge sans erreur"""
    settings = Settings.from_yaml(config_path)
    assert settings is not None
    assert isinstance(settings, Settings)


def test_get_settings_function(config_path):
    """Test la fonction get_settings()"""
    settings = get_settings(config_path)
    assert settings is not None
    assert isinstance(settings, Settings)


def test_reload_settings_function(config_path):
    """Test la fonction reload_settings()"""
    settings1 = get_settings(config_path)
    settings2 = reload_settings(config_path)
    assert settings2 is not None
    # Les deux devraient avoir les mêmes valeurs
    assert settings1.vault.path == settings2.vault.path


# =============================================================================
# Tests de validation Vault
# =============================================================================


def test_vault_path_exists(settings):
    """Test que le chemin du vault existe"""
    vault_path = Path(settings.vault.path)
    assert vault_path.exists(), f"Le vault n'existe pas: {settings.vault.path}"
    assert vault_path.is_dir(), f"Le vault n'est pas un dossier: {settings.vault.path}"


def test_vault_config_values(settings):
    """Test les valeurs de configuration du vault"""
    assert settings.vault.path
    assert settings.vault.backup_path == ".obsillama_backups"
    assert len(settings.vault.exclude_folders) > 0
    assert ".obsidian" in settings.vault.exclude_folders


# =============================================================================
# Tests de validation Ollama
# =============================================================================


def test_ollama_config_values(settings):
    """Test les valeurs de configuration Ollama"""
    assert settings.ollama.base_url == "http://localhost:11434"
    assert settings.ollama.models.generation == "mistral"
    assert settings.ollama.models.embedding == "nomic-embed-text"


def test_ollama_params_ranges(settings):
    """Test que les paramètres Ollama sont dans les bonnes plages"""
    assert 0.0 <= settings.ollama.params.temperature <= 2.0
    assert settings.ollama.params.max_tokens > 0
    assert 0.0 <= settings.ollama.params.top_p <= 1.0


# =============================================================================
# Tests de validation GraphRAG
# =============================================================================


def test_graphrag_config_values(settings):
    """Test les valeurs de configuration GraphRAG"""
    assert settings.graphrag.community_algorithm in ["leiden", "louvain"]
    assert settings.graphrag.resolution > 0.0
    assert settings.graphrag.min_community_size >= 1
    assert len(settings.graphrag.entity_types) > 0


# =============================================================================
# Tests de validation Categorization
# =============================================================================


def test_categorization_config_values(settings):
    """Test les valeurs de configuration de catégorisation"""
    assert 1 <= settings.categorization.target_count <= 100
    assert settings.categorization.min_notes_per_category >= 1
    assert settings.categorization.tag_prefix == "AI-Category-"
    assert settings.categorization.language == "fr"


def test_categorization_thresholds(settings):
    """Test les seuils de catégorisation"""
    thresholds = settings.categorization.thresholds
    assert 0.0 <= thresholds.assignment_confidence <= 1.0
    assert 0.0 <= thresholds.merge_similarity <= 1.0
    assert thresholds.subcategory_threshold >= 1


# =============================================================================
# Tests de validation LanceDB
# =============================================================================


def test_lancedb_config_values(settings):
    """Test les valeurs de configuration LanceDB"""
    assert settings.lancedb.path == "data/lancedb"
    assert settings.lancedb.index_type in ["IVF_PQ", "HNSW", "FLAT"]
    assert settings.lancedb.embedding_dim == 768  # nomic-embed-text


def test_lancedb_index_params(settings):
    """Test les paramètres d'index LanceDB"""
    params = settings.lancedb.index_params
    assert params.num_partitions >= 1
    assert params.num_sub_vectors >= 1


# =============================================================================
# Tests de validation Processing
# =============================================================================


def test_processing_config_values(settings):
    """Test les valeurs de configuration du traitement"""
    assert 1 <= settings.processing.num_workers <= 32
    assert 1 <= settings.processing.embedding_batch_size <= 128
    assert 1 <= settings.processing.note_batch_size <= 500


def test_processing_sampling(settings):
    """Test la configuration d'échantillonnage"""
    sampling = settings.processing.sampling
    assert sampling.strategy in ["random", "stratified", "all"]
    assert 1 <= sampling.percentage <= 100


# =============================================================================
# Tests de validation Logging
# =============================================================================


def test_logging_config_values(settings):
    """Test les valeurs de configuration du logging"""
    assert settings.logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert settings.logging.file == "logs/obsillama.log"
    assert isinstance(settings.logging.console, bool)


def test_logging_rotation(settings):
    """Test la configuration de rotation des logs"""
    rotation = settings.logging.rotation
    assert rotation.max_size_mb >= 1
    assert rotation.backup_count >= 1


# =============================================================================
# Tests de validation Frontmatter
# =============================================================================


def test_frontmatter_config_values(settings):
    """Test les valeurs de configuration du frontmatter"""
    assert isinstance(settings.frontmatter.preserve_structure, bool)
    assert isinstance(settings.frontmatter.preserve_comments, bool)
    assert isinstance(settings.frontmatter.backup_before_write, bool)
    assert len(settings.frontmatter.fields_to_add) > 0


# =============================================================================
# Tests de validation Incremental
# =============================================================================


def test_incremental_config_values(settings):
    """Test les valeurs de configuration du mode incrémental"""
    assert isinstance(settings.incremental.enabled, bool)
    assert settings.incremental.check_interval_days >= 1
    assert isinstance(settings.incremental.auto_ameliorate, bool)
    assert settings.incremental.recluster_threshold >= 1


# =============================================================================
# Tests d'intégration
# =============================================================================


def test_all_sections_present(settings):
    """Test que toutes les sections de configuration sont présentes"""
    assert hasattr(settings, "vault")
    assert hasattr(settings, "ollama")
    assert hasattr(settings, "graphrag")
    assert hasattr(settings, "categorization")
    assert hasattr(settings, "incremental")
    assert hasattr(settings, "frontmatter")
    assert hasattr(settings, "lancedb")
    assert hasattr(settings, "processing")
    assert hasattr(settings, "logging")
    assert hasattr(settings, "metadata")


def test_metadata(settings):
    """Test les métadonnées de configuration"""
    assert settings.metadata.config_version == "0.1.0"
    assert settings.metadata.created_at


# =============================================================================
# Script principal pour exécution manuelle
# =============================================================================


if __name__ == "__main__":
    # Permet d'exécuter les tests manuellement avec: python tests/test_config.py
    pytest.main([__file__, "-v", "--tb=short"])
