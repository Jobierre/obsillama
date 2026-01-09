"""
ObsIllama - Client Ollama

Ce module fournit une interface pour interagir avec l'API Ollama locale.
Il gère la génération de texte, les embeddings, et inclut une logique de retry robuste.
"""

import logging
from typing import List, Optional, Dict, Any

import ollama
from ollama import Client, ResponseError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from obsillama.config.settings import get_settings

# Configuration du logger
logger = logging.getLogger(__name__)


# ============================================================================
# Client Ollama avec retry logic
# ============================================================================


class OllamaClient:
    """
    Client pour interagir avec l'API Ollama.

    Cette classe fournit des méthodes pour:
    - Générer du texte avec un modèle LLM (ex: mistral)
    - Générer des embeddings vectoriels (ex: nomic-embed-text)
    - Gérer les erreurs et les timeouts
    - Retry automatique avec backoff exponentiel

    Attributes:
        client: Instance du client Ollama
        generation_model: Nom du modèle pour la génération de texte
        embedding_model: Nom du modèle pour les embeddings
        generation_params: Paramètres par défaut pour la génération
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        generation_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialise le client Ollama.

        Args:
            base_url: URL de base de l'API Ollama (défaut: depuis config)
            generation_model: Modèle pour la génération (défaut: depuis config)
            embedding_model: Modèle pour les embeddings (défaut: depuis config)
            timeout: Timeout pour les requêtes en secondes (défaut: 120s)
        """
        # Charger la configuration
        settings = get_settings()

        # Configuration de la connexion
        self.base_url = base_url or settings.ollama.base_url
        self.generation_model = generation_model or settings.ollama.models.generation
        self.embedding_model = embedding_model or settings.ollama.models.embedding

        # Paramètres de génération par défaut
        self.generation_params = {
            "temperature": settings.ollama.params.temperature,
            "num_predict": settings.ollama.params.max_tokens,
            "top_p": settings.ollama.params.top_p,
        }

        # Créer le client Ollama
        try:
            self.client = Client(
                host=self.base_url,
                timeout=timeout,
            )
            logger.info(
                f"Client Ollama initialisé: {self.base_url} "
                f"(generation={self.generation_model}, embedding={self.embedding_model})"
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Ollama: {e}")
            raise

    def test_connection(self) -> bool:
        """
        Test la connexion à Ollama.

        Returns:
            bool: True si la connexion fonctionne, False sinon
        """
        try:
            # Tester en listant les modèles disponibles
            response = self.client.list()
            logger.info(f"Connexion Ollama OK - {len(response.models)} modèles disponibles")
            return True
        except Exception as e:
            logger.error(f"Échec de connexion à Ollama: {e}")
            return False

    @retry(
        retry=retry_if_exception_type((ResponseError, ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Génère du texte à partir d'un prompt.

        Cette méthode utilise retry automatique avec backoff exponentiel:
        - 3 tentatives maximum
        - Attente: 2s, 4s, 8s (max 10s)
        - Retry sur: ResponseError, ConnectionError, TimeoutError

        Args:
            prompt: Le prompt à envoyer au modèle
            model: Modèle à utiliser (défaut: self.generation_model)
            system: Prompt système optionnel
            options: Paramètres de génération personnalisés

        Returns:
            str: Le texte généré par le modèle

        Raises:
            ResponseError: Si l'API Ollama retourne une erreur
            ConnectionError: Si la connexion échoue
            TimeoutError: Si la requête timeout
        """
        model = model or self.generation_model
        options = options or self.generation_params.copy()

        logger.debug(
            f"Génération avec {model} - prompt: {prompt[:100]}... "
            f"(system={bool(system)})"
        )

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options,
            )

            generated_text = response.response

            logger.info(
                f"Génération réussie - model={model}, "
                f"tokens={response.eval_count}, "
                f"durée={response.total_duration / 1e9:.2f}s"
            )

            return generated_text

        except ResponseError as e:
            logger.error(
                f"Erreur API Ollama (generate): {e.error} "
                f"(status={e.status_code})"
            )
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la génération: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((ResponseError, ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """
        Génère un embedding vectoriel pour un texte.

        Cette méthode utilise retry automatique avec backoff exponentiel:
        - 3 tentatives maximum
        - Attente: 2s, 4s, 8s (max 10s)
        - Retry sur: ResponseError, ConnectionError, TimeoutError

        Args:
            text: Le texte à encoder
            model: Modèle à utiliser (défaut: self.embedding_model)

        Returns:
            List[float]: Le vecteur d'embedding (dimension selon le modèle)

        Raises:
            ResponseError: Si l'API Ollama retourne une erreur
            ConnectionError: Si la connexion échoue
            TimeoutError: Si la requête timeout
        """
        model = model or self.embedding_model

        logger.debug(
            f"Embedding avec {model} - text: {text[:100]}... "
            f"(len={len(text)})"
        )

        try:
            response = self.client.embed(
                model=model,
                input=text,
            )

            embedding = response.embeddings[0]

            logger.debug(
                f"Embedding réussi - model={model}, dim={len(embedding)}"
            )

            return embedding

        except ResponseError as e:
            logger.error(
                f"Erreur API Ollama (embed): {e.error} "
                f"(status={e.status_code})"
            )
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'embedding: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((ResponseError, ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def embed_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes.

        Cette méthode utilise retry automatique avec backoff exponentiel:
        - 3 tentatives maximum
        - Attente: 2s, 4s, 8s (max 10s)
        - Retry sur: ResponseError, ConnectionError, TimeoutError

        Note: L'API Ollama supporte nativement le batch d'embeddings,
        donc on envoie tous les textes en une seule requête.

        Args:
            texts: Liste des textes à encoder
            model: Modèle à utiliser (défaut: self.embedding_model)
            show_progress: Afficher la progression (pour debug)

        Returns:
            List[List[float]]: Liste des vecteurs d'embedding

        Raises:
            ResponseError: Si l'API Ollama retourne une erreur
            ConnectionError: Si la connexion échoue
            TimeoutError: Si la requête timeout
        """
        model = model or self.embedding_model

        if not texts:
            logger.warning("Liste de textes vide pour embed_batch")
            return []

        logger.info(
            f"Embedding batch avec {model} - {len(texts)} textes"
        )

        try:
            response = self.client.embed(
                model=model,
                input=texts,
            )

            embeddings = response.embeddings

            logger.info(
                f"Embedding batch réussi - model={model}, "
                f"count={len(embeddings)}, dim={len(embeddings[0]) if embeddings else 0}"
            )

            if show_progress:
                logger.debug(f"Embeddings générés: {len(embeddings)}/{len(texts)}")

            return embeddings

        except ResponseError as e:
            logger.error(
                f"Erreur API Ollama (embed_batch): {e.error} "
                f"(status={e.status_code})"
            )
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'embedding batch: {e}")
            raise

    def list_models(self) -> List[str]:
        """
        Liste les modèles disponibles sur le serveur Ollama.

        Returns:
            List[str]: Liste des noms de modèles
        """
        try:
            response = self.client.list()
            models = [model.model for model in response.models]
            logger.info(f"Modèles disponibles: {', '.join(models)}")
            return models
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des modèles: {e}")
            return []

    def __repr__(self) -> str:
        """Représentation string du client."""
        return (
            f"OllamaClient(base_url='{self.base_url}', "
            f"generation='{self.generation_model}', "
            f"embedding='{self.embedding_model}')"
        )
