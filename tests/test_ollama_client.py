"""
Tests pour le client Ollama

Ces tests vérifient le bon fonctionnement du client Ollama:
- Connexion à l'API
- Génération de texte
- Génération d'embeddings
- Retry logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ollama import ResponseError

from obsillama.llm.ollama_client import OllamaClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ollama_client():
    """Fixture pour créer un client Ollama de test."""
    # On utilise les paramètres par défaut de la config
    return OllamaClient()


@pytest.fixture
def mock_ollama_response_generate():
    """Mock d'une réponse Ollama pour generate()."""
    mock_response = Mock()
    mock_response.response = "Ceci est une réponse générée par le modèle."
    mock_response.eval_count = 42
    mock_response.total_duration = 1_500_000_000  # 1.5 secondes en nanosecondes
    return mock_response


@pytest.fixture
def mock_ollama_response_embed():
    """Mock d'une réponse Ollama pour embed()."""
    mock_response = Mock()
    # Simuler un embedding de dimension 768 (nomic-embed-text)
    mock_response.embeddings = [[0.1] * 768]
    return mock_response


@pytest.fixture
def mock_ollama_response_embed_batch():
    """Mock d'une réponse Ollama pour embed_batch()."""
    mock_response = Mock()
    # Simuler 10 embeddings de dimension 768
    mock_response.embeddings = [[0.1] * 768 for _ in range(10)]
    return mock_response


@pytest.fixture
def mock_ollama_list():
    """Mock pour la méthode list() de Ollama."""
    mock_response = Mock()
    mock_model_1 = Mock()
    mock_model_1.model = "mistral"
    mock_model_2 = Mock()
    mock_model_2.model = "nomic-embed-text"
    mock_response.models = [mock_model_1, mock_model_2]
    return mock_response


# ============================================================================
# Tests d'initialisation
# ============================================================================


def test_ollama_client_initialization(ollama_client):
    """Test que le client s'initialise correctement."""
    assert ollama_client is not None
    # Vérifier que l'URL est valide (peut être localhost ou IP distante)
    assert ollama_client.base_url.startswith("http://") or ollama_client.base_url.startswith("https://")
    assert "11434" in ollama_client.base_url  # Port Ollama par défaut
    assert ollama_client.generation_model == "mistral"
    assert ollama_client.embedding_model == "nomic-embed-text"
    assert ollama_client.client is not None


def test_ollama_client_custom_params():
    """Test l'initialisation avec des paramètres personnalisés."""
    client = OllamaClient(
        base_url="http://custom:8080",
        generation_model="llama3",
        embedding_model="custom-embed",
        timeout=60.0,
    )
    assert client.base_url == "http://custom:8080"
    assert client.generation_model == "llama3"
    assert client.embedding_model == "custom-embed"


def test_ollama_client_repr(ollama_client):
    """Test la représentation string du client."""
    repr_str = repr(ollama_client)
    assert "OllamaClient" in repr_str
    # Vérifier que l'URL est présente (localhost ou IP distante)
    assert "11434" in repr_str  # Port Ollama
    assert "mistral" in repr_str
    assert "nomic-embed-text" in repr_str


# ============================================================================
# Tests de connexion
# ============================================================================


def test_connection_success(ollama_client, mock_ollama_list):
    """Test que la connexion à Ollama fonctionne."""
    with patch.object(ollama_client.client, "list", return_value=mock_ollama_list):
        result = ollama_client.test_connection()
        assert result is True


def test_connection_failure(ollama_client):
    """Test la gestion d'échec de connexion."""
    with patch.object(
        ollama_client.client, "list", side_effect=ConnectionError("Connection failed")
    ):
        result = ollama_client.test_connection()
        assert result is False


def test_list_models(ollama_client, mock_ollama_list):
    """Test la récupération de la liste des modèles."""
    with patch.object(ollama_client.client, "list", return_value=mock_ollama_list):
        models = ollama_client.list_models()
        assert len(models) == 2
        assert "mistral" in models
        assert "nomic-embed-text" in models


# ============================================================================
# Tests de génération de texte
# ============================================================================


def test_generate_success(ollama_client, mock_ollama_response_generate):
    """Test la génération de texte."""
    with patch.object(
        ollama_client.client, "generate", return_value=mock_ollama_response_generate
    ):
        result = ollama_client.generate("Bonjour, comment vas-tu ?")
        assert result == "Ceci est une réponse générée par le modèle."


def test_generate_with_system_prompt(ollama_client, mock_ollama_response_generate):
    """Test la génération avec un prompt système."""
    with patch.object(
        ollama_client.client, "generate", return_value=mock_ollama_response_generate
    ):
        result = ollama_client.generate(
            prompt="Explique Python",
            system="Tu es un professeur de programmation.",
        )
        assert result == "Ceci est une réponse générée par le modèle."


def test_generate_with_custom_options(ollama_client, mock_ollama_response_generate):
    """Test la génération avec des options personnalisées."""
    with patch.object(
        ollama_client.client, "generate", return_value=mock_ollama_response_generate
    ):
        result = ollama_client.generate(
            prompt="Test",
            options={"temperature": 0.8, "num_predict": 500},
        )
        assert result == "Ceci est une réponse générée par le modèle."


def test_generate_with_custom_model(ollama_client, mock_ollama_response_generate):
    """Test la génération avec un modèle personnalisé."""
    with patch.object(
        ollama_client.client, "generate", return_value=mock_ollama_response_generate
    ):
        result = ollama_client.generate(
            prompt="Test",
            model="llama3",
        )
        assert result == "Ceci est une réponse générée par le modèle."


def test_generate_response_error(ollama_client):
    """Test la gestion d'erreur API lors de la génération."""
    mock_error = ResponseError("Model not found", status_code=404)
    with patch.object(ollama_client.client, "generate", side_effect=mock_error):
        with pytest.raises(ResponseError):
            ollama_client.generate("Test")


# ============================================================================
# Tests d'embeddings
# ============================================================================


def test_embed_success(ollama_client, mock_ollama_response_embed):
    """Test la génération d'embedding."""
    with patch.object(
        ollama_client.client, "embed", return_value=mock_ollama_response_embed
    ):
        result = ollama_client.embed("Test d'embedding en français")
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)


def test_embed_with_custom_model(ollama_client, mock_ollama_response_embed):
    """Test l'embedding avec un modèle personnalisé."""
    with patch.object(
        ollama_client.client, "embed", return_value=mock_ollama_response_embed
    ):
        result = ollama_client.embed(
            text="Test",
            model="custom-embed",
        )
        assert len(result) == 768


def test_embed_response_error(ollama_client):
    """Test la gestion d'erreur API lors de l'embedding."""
    mock_error = ResponseError("Model not found", status_code=404)
    with patch.object(ollama_client.client, "embed", side_effect=mock_error):
        with pytest.raises(ResponseError):
            ollama_client.embed("Test")


# ============================================================================
# Tests d'embeddings batch
# ============================================================================


def test_embed_batch_success(ollama_client, mock_ollama_response_embed_batch):
    """Test la génération d'embeddings en batch."""
    texts = [
        "Premier texte",
        "Deuxième texte",
        "Troisième texte",
        "Quatrième texte",
        "Cinquième texte",
        "Sixième texte",
        "Septième texte",
        "Huitième texte",
        "Neuvième texte",
        "Dixième texte",
    ]

    with patch.object(
        ollama_client.client, "embed", return_value=mock_ollama_response_embed_batch
    ):
        results = ollama_client.embed_batch(texts)
        assert len(results) == 10
        assert all(len(emb) == 768 for emb in results)


def test_embed_batch_empty_list(ollama_client):
    """Test l'embedding batch avec une liste vide."""
    result = ollama_client.embed_batch([])
    assert result == []


def test_embed_batch_with_progress(ollama_client, mock_ollama_response_embed_batch):
    """Test l'embedding batch avec affichage de progression."""
    texts = ["Texte 1", "Texte 2", "Texte 3"]

    with patch.object(
        ollama_client.client, "embed", return_value=mock_ollama_response_embed_batch
    ):
        results = ollama_client.embed_batch(texts, show_progress=True)
        assert len(results) == 10  # Mock retourne toujours 10


def test_embed_batch_with_custom_model(
    ollama_client, mock_ollama_response_embed_batch
):
    """Test l'embedding batch avec un modèle personnalisé."""
    texts = ["Texte 1", "Texte 2"]

    with patch.object(
        ollama_client.client, "embed", return_value=mock_ollama_response_embed_batch
    ):
        results = ollama_client.embed_batch(texts, model="custom-embed")
        assert len(results) == 10


# ============================================================================
# Tests de retry logic
# ============================================================================


def test_generate_retry_on_timeout(ollama_client, mock_ollama_response_generate):
    """Test que generate() retry sur TimeoutError."""
    # Simuler 2 timeouts puis succès
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise TimeoutError("Request timeout")
        return mock_ollama_response_generate

    with patch.object(ollama_client.client, "generate", side_effect=side_effect):
        result = ollama_client.generate("Test")
        assert result == "Ceci est une réponse générée par le modèle."
        assert call_count == 3  # 2 échecs + 1 succès


def test_embed_retry_on_connection_error(ollama_client, mock_ollama_response_embed):
    """Test que embed() retry sur ConnectionError."""
    # Simuler 1 connection error puis succès
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Connection lost")
        return mock_ollama_response_embed

    with patch.object(ollama_client.client, "embed", side_effect=side_effect):
        result = ollama_client.embed("Test")
        assert len(result) == 768
        assert call_count == 2  # 1 échec + 1 succès


def test_retry_max_attempts_exceeded(ollama_client):
    """Test que retry s'arrête après max attempts."""
    # Simuler 3 timeouts (dépassement du max)
    with patch.object(
        ollama_client.client, "generate", side_effect=TimeoutError("Timeout")
    ):
        with pytest.raises(TimeoutError):
            ollama_client.generate("Test")


def test_retry_does_not_catch_other_exceptions(ollama_client):
    """Test que retry ne catch pas les autres exceptions."""
    # ValueError ne devrait pas trigger de retry
    with patch.object(
        ollama_client.client, "generate", side_effect=ValueError("Invalid input")
    ):
        with pytest.raises(ValueError):
            ollama_client.generate("Test")


# ============================================================================
# Tests d'intégration (nécessitent Ollama en cours d'exécution)
# ============================================================================


@pytest.mark.integration
def test_real_connection():
    """
    Test réel de connexion à Ollama.

    Note: Ce test nécessite qu'Ollama soit en cours d'exécution.
    Marqué avec @pytest.mark.integration pour être skippé par défaut.
    """
    client = OllamaClient()
    assert client.test_connection() is True


@pytest.mark.integration
def test_real_generate():
    """
    Test réel de génération avec Ollama.

    Note: Ce test nécessite qu'Ollama soit en cours d'exécution avec mistral.
    """
    client = OllamaClient()
    response = client.generate("Bonjour, comment vas-tu ?")
    assert response is not None
    assert len(response) > 0


@pytest.mark.integration
def test_real_embed():
    """
    Test réel d'embedding avec Ollama.

    Note: Ce test nécessite qu'Ollama soit en cours d'exécution avec nomic-embed-text.
    """
    client = OllamaClient()
    embedding = client.embed("Test d'embedding en français")
    assert len(embedding) == 768
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.integration
def test_real_embed_batch():
    """
    Test réel d'embedding batch avec Ollama.

    Note: Ce test nécessite qu'Ollama soit en cours d'exécution avec nomic-embed-text.
    """
    client = OllamaClient()
    texts = [
        "Premier texte",
        "Deuxième texte",
        "Troisième texte",
        "Quatrième texte",
        "Cinquième texte",
        "Sixième texte",
        "Septième texte",
        "Huitième texte",
        "Neuvième texte",
        "Dixième texte",
    ]
    embeddings = client.embed_batch(texts)
    assert len(embeddings) == 10
    assert all(len(emb) == 768 for emb in embeddings)
