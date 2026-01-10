"""
ObsIllama - Gestionnaire d'embeddings

Ce module gère la génération et le cache des embeddings vectoriels
pour les notes et catégories.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from tqdm import tqdm

from obsillama.llm.ollama_client import OllamaClient
from obsillama.models.note import Note
from obsillama.models.embedding import Embedding

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Gestionnaire pour la génération d'embeddings vectoriels.

    Cette classe gère:
    - Génération d'embeddings via Ollama
    - Cache des embeddings (pour éviter recalculs)
    - Traitement par batch avec progress bar
    - Mise à jour des métadonnées des notes
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        cache_path: Optional[Path] = None,
        model_name: str = "nomic-embed-text",
        model_dimension: int = 768,
    ):
        """
        Initialise le gestionnaire d'embeddings.

        Args:
            ollama_client: Client Ollama pour génération d'embeddings
            cache_path: Chemin vers le fichier de cache JSON (optionnel)
            model_name: Nom du modèle d'embedding
            model_dimension: Dimension des vecteurs d'embedding
        """
        self.ollama_client = ollama_client
        self.model_name = model_name
        self.model_dimension = model_dimension

        # Cache en mémoire et sur disque
        self.cache_path = cache_path
        self._cache: Dict[str, List[float]] = {}

        # Charger le cache depuis le disque si disponible
        if self.cache_path and self.cache_path.exists():
            self._load_cache()

        logger.info(
            f"EmbeddingManager initialisé - model={model_name}, "
            f"dim={model_dimension}, cache_size={len(self._cache)}"
        )

    def _compute_content_hash(self, text: str) -> str:
        """
        Calcule le hash SHA256 d'un texte pour le cache.

        Args:
            text: Texte à hasher

        Returns:
            str: Hash SHA256 hexadécimal
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load_cache(self) -> None:
        """Charge le cache depuis le disque"""
        try:
            if not self.cache_path or not self.cache_path.exists():
                return

            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            self._cache = cache_data.get("embeddings", {})

            logger.info(f"Cache chargé - {len(self._cache)} embeddings")

        except Exception as e:
            logger.warning(f"Erreur lors du chargement du cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Sauvegarde le cache sur le disque"""
        try:
            if not self.cache_path:
                return

            # Créer le dossier parent si nécessaire
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "model_name": self.model_name,
                "model_dimension": self.model_dimension,
                "last_updated": datetime.now().isoformat(),
                "embeddings": self._cache,
            }

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Cache sauvegardé - {len(self._cache)} embeddings")

        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du cache: {e}")

    def generate_embedding(
        self,
        text: str,
        use_cache: bool = True,
        max_length: int = 2000,
    ) -> List[float]:
        """
        Génère un embedding vectoriel pour un texte.

        Args:
            text: Texte à encoder
            use_cache: Si True, utilise le cache pour éviter recalculs
            max_length: Longueur maximale en caractères (troncature si dépassement)

        Returns:
            List[float]: Vecteur d'embedding (768 dimensions)

        Raises:
            ValueError: Si le texte est vide
        """
        if not text or not text.strip():
            raise ValueError("Le texte ne peut pas être vide")

        # Tronquer si trop long
        if len(text) > max_length:
            logger.debug(f"Texte tronqué: {len(text)} -> {max_length} chars")
            text = text[:max_length]

        # Vérifier le cache
        if use_cache:
            content_hash = self._compute_content_hash(text)

            if content_hash in self._cache:
                logger.debug(f"Embedding trouvé dans le cache (hash={content_hash[:8]}...)")
                return self._cache[content_hash]

        # Générer l'embedding via Ollama
        logger.debug(f"Génération embedding - text_len={len(text)}")

        embedding = self.ollama_client.embed(
            text=text,
            model=self.model_name,
        )

        # Valider la dimension
        if len(embedding) != self.model_dimension:
            raise ValueError(
                f"Dimension d'embedding invalide: {len(embedding)} != {self.model_dimension}"
            )

        # Mettre en cache
        if use_cache:
            content_hash = self._compute_content_hash(text)
            self._cache[content_hash] = embedding

            # Sauvegarder périodiquement (tous les 10 nouveaux embeddings)
            if len(self._cache) % 10 == 0:
                self._save_cache()

        return embedding

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        use_cache: bool = True,
        show_progress: bool = True,
    ) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes avec traitement par batch.

        Args:
            texts: Liste de textes à encoder
            batch_size: Taille des batchs pour l'API Ollama
            use_cache: Si True, utilise le cache
            show_progress: Si True, affiche une progress bar

        Returns:
            List[List[float]]: Liste des vecteurs d'embedding
        """
        if not texts:
            logger.warning("Liste de textes vide")
            return []

        logger.info(f"Génération embeddings batch - count={len(texts)}, batch_size={batch_size}")

        embeddings: List[List[float]] = []
        texts_to_generate: List[str] = []
        cache_indices: Dict[int, str] = {}  # index -> content_hash

        # Séparer les textes cachés et non-cachés
        for i, text in enumerate(texts):
            if not text or not text.strip():
                logger.warning(f"Texte vide à l'index {i}, utilisation d'un vecteur zéro")
                embeddings.append([0.0] * self.model_dimension)
                continue

            if use_cache:
                content_hash = self._compute_content_hash(text)

                if content_hash in self._cache:
                    embeddings.append(self._cache[content_hash])
                    cache_indices[i] = content_hash
                    continue

            # Texte non caché, à générer
            texts_to_generate.append(text)

        logger.info(
            f"Cache hits: {len(cache_indices)}/{len(texts)} "
            f"({100 * len(cache_indices) / len(texts):.1f}%)"
        )

        # Générer les embeddings manquants par batch
        if texts_to_generate:
            if show_progress:
                pbar = tqdm(
                    total=len(texts_to_generate),
                    desc="Génération embeddings",
                    unit="text",
                )

            for i in range(0, len(texts_to_generate), batch_size):
                batch = texts_to_generate[i : i + batch_size]

                # Appeler l'API Ollama
                batch_embeddings = self.ollama_client.embed_batch(
                    texts=batch,
                    model=self.model_name,
                )

                # Mettre en cache et ajouter aux résultats
                for text, embedding in zip(batch, batch_embeddings):
                    if use_cache:
                        content_hash = self._compute_content_hash(text)
                        self._cache[content_hash] = embedding

                    embeddings.append(embedding)

                if show_progress:
                    pbar.update(len(batch))

            if show_progress:
                pbar.close()

            # Sauvegarder le cache
            if use_cache:
                self._save_cache()

        logger.info(f"Embeddings générés - total={len(embeddings)}")

        return embeddings

    def embed_notes(
        self,
        notes: List[Note],
        batch_size: int = 8,
        use_cache: bool = True,
        show_progress: bool = True,
        max_length: int = 2000,
    ) -> List[Note]:
        """
        Génère des embeddings pour une liste de notes.

        Met à jour les métadonnées des notes (has_embedding, embedding_model, embedding_date)
        mais ne stocke PAS le vecteur dans l'objet Note (stocké séparément dans LanceDB).

        Args:
            notes: Liste de notes à encoder
            batch_size: Taille des batchs
            use_cache: Si True, utilise le cache
            show_progress: Si True, affiche une progress bar
            max_length: Longueur maximale en caractères (troncature si dépassement)

        Returns:
            List[Note]: Notes avec métadonnées d'embedding mises à jour
        """
        if not notes:
            logger.warning("Liste de notes vide")
            return []

        logger.info(f"Génération embeddings pour {len(notes)} notes")

        # Extraire les textes à encoder (titre + contenu)
        texts = []
        for note in notes:
            # Combiner titre et contenu pour l'embedding
            text = f"{note.title}\n\n{note.content}"

            # Tronquer si trop long (modèle d'embedding a une limite de contexte)
            if len(text) > max_length:
                logger.debug(
                    f"Note '{note.title}' tronquée: {len(text)} -> {max_length} chars"
                )
                text = text[:max_length]

            texts.append(text)

        # Générer les embeddings
        embeddings = self.generate_embeddings_batch(
            texts=texts,
            batch_size=batch_size,
            use_cache=use_cache,
            show_progress=show_progress,
        )

        # Mettre à jour les métadonnées des notes
        updated_notes = []
        for note, embedding in zip(notes, embeddings):
            # Créer une copie mise à jour
            note_dict = note.model_dump()
            note_dict["has_embedding"] = True
            note_dict["embedding_model"] = self.model_name
            note_dict["embedding_date"] = datetime.now()

            updated_note = Note(**note_dict)
            updated_notes.append(updated_note)

        logger.info(f"Embeddings générés pour {len(updated_notes)} notes")

        return updated_notes

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings.

        Args:
            embedding1: Premier vecteur
            embedding2: Deuxième vecteur

        Returns:
            float: Similarité cosinus (entre 0 et 1)

        Raises:
            ValueError: Si les dimensions ne correspondent pas
        """
        import numpy as np

        if len(embedding1) != len(embedding2):
            raise ValueError(
                f"Dimensions incompatibles: {len(embedding1)} != {len(embedding2)}"
            )

        vec1 = np.array(embedding1, dtype=np.float32)
        vec2 = np.array(embedding2, dtype=np.float32)

        # Normaliser
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Similarité cosinus
        similarity = float(np.dot(vec1, vec2) / (norm1 * norm2))

        # Borner entre 0 et 1
        return max(0.0, min(1.0, similarity))

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le cache.

        Returns:
            Dict: Statistiques du cache
        """
        return {
            "cache_size": len(self._cache),
            "cache_path": str(self.cache_path) if self.cache_path else None,
            "model_name": self.model_name,
            "model_dimension": self.model_dimension,
        }

    def clear_cache(self) -> None:
        """Vide le cache en mémoire et sur disque"""
        self._cache.clear()

        if self.cache_path and self.cache_path.exists():
            self.cache_path.unlink()

        logger.info("Cache vidé")
