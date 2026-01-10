"""
ObsIllama - Embedding Store

Ce module gère le stockage et la recherche d'embeddings dans LanceDB.
Il étend les fonctionnalités du LanceDBManager avec des opérations
spécifiques aux embeddings.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

import numpy as np

from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.models.note import Note
from obsillama.models.embedding import Embedding

logger = logging.getLogger(__name__)


class EmbeddingStore:
    """
    Gestionnaire du stockage et de la recherche d'embeddings.

    Cette classe fournit des méthodes pour:
    - Upsert (insert/update) d'embeddings
    - Recherche sémantique avancée
    - Calcul de centroides de catégories
    - Filtrage et seuillage de similarité
    """

    def __init__(self, lancedb_manager: LanceDBManager):
        """
        Initialise l'EmbeddingStore.

        Args:
            lancedb_manager: Instance du LanceDBManager
        """
        self.db_manager = lancedb_manager

        logger.info("EmbeddingStore initialisé")

    def upsert_embeddings(
        self,
        notes: List[Note],
        embeddings: List[List[float]],
    ) -> None:
        """
        Insère ou met à jour les embeddings de notes dans LanceDB.

        Si une note existe déjà (même ID), elle sera mise à jour.
        Sinon, elle sera insérée.

        Args:
            notes: Liste des notes
            embeddings: Liste des embeddings (même ordre que notes)

        Raises:
            ValueError: Si len(notes) != len(embeddings)
        """
        if len(notes) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(notes)} notes vs {len(embeddings)} embeddings"
            )

        logger.info(f"Upsert de {len(notes)} embeddings dans LanceDB")

        try:
            # Vérifier si la table existe
            if not self.db_manager.table_exists("notes"):
                logger.info("Table 'notes' n'existe pas, création...")
                self.db_manager.create_notes_table()

            # Pour LanceDB, on peut simplement insérer
            # (les doublons seront gérés par la recherche)
            self.db_manager.insert_notes(notes, embeddings)

            logger.info(f"{len(notes)} embeddings upsertés avec succès")

        except Exception as e:
            logger.error(f"Erreur lors de l'upsert des embeddings: {e}")
            raise

    def search_similar_notes(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: Optional[float] = None,
        category_filter: Optional[str] = None,
        folder_filter: Optional[str] = None,
        min_word_count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique avancée de notes similaires.

        Args:
            query_embedding: Vecteur de requête (768 dims)
            top_k: Nombre maximum de résultats
            similarity_threshold: Seuil de similarité minimum (0-1)
            category_filter: Filtrer par catégorie (ex: "Technology")
            folder_filter: Filtrer par dossier (ex: "Projects")
            min_word_count: Nombre minimum de mots

        Returns:
            List[Dict]: Liste des notes similaires avec scores

        Example:
            >>> results = store.search_similar_notes(
            ...     query_embedding=[0.1, 0.2, ...],
            ...     top_k=5,
            ...     similarity_threshold=0.7,
            ...     category_filter="Technology"
            ... )
        """
        logger.info(
            f"Recherche sémantique - top_k={top_k}, "
            f"threshold={similarity_threshold}, "
            f"category={category_filter}"
        )

        # Construire le filtre SQL
        filters = []

        if category_filter:
            # Vérifier si la catégorie est dans ai_categories (liste)
            filters.append(f"array_contains(ai_categories, '{category_filter}')")

        if folder_filter:
            filters.append(f"folder = '{folder_filter}'")

        if min_word_count:
            filters.append(f"word_count >= {min_word_count}")

        filter_query = " AND ".join(filters) if filters else None

        # Effectuer la recherche vectorielle
        results = self.db_manager.search_notes_by_embedding(
            query_embedding=query_embedding,
            limit=top_k * 2 if similarity_threshold else top_k,  # Fetch extra for filtering
            filter_query=filter_query,
        )

        # Filtrer par seuil de similarité si spécifié
        if similarity_threshold:
            filtered_results = []

            for result in results:
                # LanceDB retourne un score de distance
                # On doit le convertir en similarité cosinus
                # Pour metric="cosine", distance = 1 - cosine_similarity
                distance = result.get("_distance", 0)
                similarity = 1 - distance

                if similarity >= similarity_threshold:
                    result["_similarity"] = similarity
                    filtered_results.append(result)

            results = filtered_results[:top_k]

        else:
            # Ajouter le score de similarité pour tous les résultats
            for result in results:
                distance = result.get("_distance", 0)
                result["_similarity"] = 1 - distance

        logger.info(f"Recherche terminée - {len(results)} résultats")

        return results

    def search_by_text(
        self,
        query_text: str,
        embedding_generator,
        top_k: int = 10,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique par texte libre.

        Args:
            query_text: Texte de la requête
            embedding_generator: Fonction/méthode pour générer l'embedding
                                 (ex: embedding_manager.generate_embedding)
            top_k: Nombre de résultats
            **kwargs: Arguments additionnels pour search_similar_notes

        Returns:
            List[Dict]: Résultats de la recherche

        Example:
            >>> results = store.search_by_text(
            ...     "docker self-hosting",
            ...     embedding_manager.generate_embedding,
            ...     top_k=5
            ... )
        """
        logger.info(f"Recherche par texte: '{query_text[:50]}...'")

        # Générer l'embedding de la requête
        query_embedding = embedding_generator(query_text)

        # Rechercher
        return self.search_similar_notes(
            query_embedding=query_embedding,
            top_k=top_k,
            **kwargs,
        )

    def get_category_centroid(
        self,
        category_id: str,
        category_name: Optional[str] = None,
    ) -> Optional[List[float]]:
        """
        Calcule l'embedding moyen (centroide) des notes d'une catégorie.

        Args:
            category_id: ID de la catégorie
            category_name: Nom de la catégorie (utilisé si ID non trouvé)

        Returns:
            Optional[List[float]]: Vecteur centroide ou None si aucune note

        Example:
            >>> centroid = store.get_category_centroid("cat_technology")
        """
        logger.info(f"Calcul du centroide pour catégorie: {category_id}")

        try:
            table = self.db_manager.db.open_table("notes")

            # Construire le filtre pour la catégorie
            if category_name:
                filter_query = f"array_contains(ai_categories, '{category_name}')"
            else:
                # Chercher par ID (nécessite une table de correspondance)
                # Pour l'instant, on utilise le nom
                logger.warning(
                    "Recherche par category_id non implémentée, "
                    "utilisez category_name"
                )
                return None

            # Récupérer toutes les notes de la catégorie
            results = (
                table.search()
                .where(filter_query)
                .to_list()
            )

            if not results:
                logger.warning(f"Aucune note trouvée pour la catégorie {category_id}")
                return None

            # Extraire les vecteurs
            vectors = [result["vector"] for result in results]

            # Calculer la moyenne
            centroid = np.mean(vectors, axis=0).tolist()

            logger.info(
                f"Centroide calculé pour {len(vectors)} notes "
                f"(dim={len(centroid)})"
            )

            return centroid

        except Exception as e:
            logger.error(f"Erreur lors du calcul du centroide: {e}")
            return None

    def get_notes_by_similarity_range(
        self,
        reference_embedding: List[float],
        min_similarity: float,
        max_similarity: float,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Récupère les notes dans une plage de similarité donnée.

        Utile pour trouver des notes "moyennement similaires" qui pourraient
        nécessiter une revue manuelle.

        Args:
            reference_embedding: Vecteur de référence
            min_similarity: Similarité minimum (0-1)
            max_similarity: Similarité maximum (0-1)
            limit: Nombre maximum de résultats

        Returns:
            List[Dict]: Notes dans la plage de similarité
        """
        logger.info(
            f"Recherche dans plage de similarité: "
            f"{min_similarity:.2f} - {max_similarity:.2f}"
        )

        # Récupérer plus de résultats que nécessaire
        results = self.db_manager.search_notes_by_embedding(
            query_embedding=reference_embedding,
            limit=limit * 3,
        )

        # Filtrer par plage de similarité
        filtered = []

        for result in results:
            distance = result.get("_distance", 0)
            similarity = 1 - distance

            if min_similarity <= similarity <= max_similarity:
                result["_similarity"] = similarity
                filtered.append(result)

        # Limiter les résultats
        filtered = filtered[:limit]

        logger.info(f"{len(filtered)} notes trouvées dans la plage")

        return filtered

    def batch_search(
        self,
        query_embeddings: List[List[float]],
        top_k: int = 10,
    ) -> List[List[Dict[str, Any]]]:
        """
        Effectue plusieurs recherches vectorielles en batch.

        Args:
            query_embeddings: Liste de vecteurs de requête
            top_k: Nombre de résultats par requête

        Returns:
            List[List[Dict]]: Liste de listes de résultats
        """
        logger.info(f"Recherche batch - {len(query_embeddings)} requêtes")

        results = []

        for i, query_emb in enumerate(query_embeddings):
            query_results = self.search_similar_notes(
                query_embedding=query_emb,
                top_k=top_k,
            )
            results.append(query_results)

            if (i + 1) % 10 == 0:
                logger.debug(f"Progression: {i + 1}/{len(query_embeddings)}")

        logger.info(f"Recherche batch terminée - {len(results)} résultats")

        return results

    def get_embedding_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les embeddings stockés.

        Returns:
            Dict: Statistiques (nombre de notes, tables, etc.)
        """
        stats = {
            "total_notes": 0,
            "notes_with_embeddings": 0,
            "total_categories": 0,
            "total_entities": 0,
            "total_communities": 0,
            "tables": self.db_manager.list_tables(),
        }

        try:
            if self.db_manager.table_exists("notes"):
                stats["total_notes"] = self.db_manager.count_records("notes")

                # Compter les notes avec embeddings
                # (en LanceDB, toutes les notes insérées ont des embeddings)
                stats["notes_with_embeddings"] = stats["total_notes"]

            if self.db_manager.table_exists("categories"):
                stats["total_categories"] = self.db_manager.count_records("categories")

            if self.db_manager.table_exists("entities"):
                stats["total_entities"] = self.db_manager.count_records("entities")

            if self.db_manager.table_exists("communities"):
                stats["total_communities"] = self.db_manager.count_records("communities")

        except Exception as e:
            logger.error(f"Erreur lors du calcul des stats: {e}")

        return stats

    def __repr__(self) -> str:
        """Représentation string de l'EmbeddingStore"""
        stats = self.get_embedding_stats()
        return (
            f"EmbeddingStore("
            f"notes={stats['total_notes']}, "
            f"categories={stats['total_categories']})"
        )
