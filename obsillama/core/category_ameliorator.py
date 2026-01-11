"""
ObsIllama - Category Ameliorator

Ce module gère l'amélioration incrémentale des catégories existantes.
Au lieu de relancer GraphRAG, il assigne les nouvelles notes aux catégories
existantes et suggère des améliorations (sous-catégories, fusions).
"""

import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime

import numpy as np
from sklearn.cluster import KMeans

from obsillama.models.note import Note
from obsillama.models.category import Category, ReviewStatus
from obsillama.storage.category_store import CategoryStore
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.core.category_generator import (
    generate_category_id,
    cosine_similarity,
)
from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.prompts.categorization import get_subcategory_suggestion_prompt
from obsillama.llm.graphrag_integration import safe_json_parse

logger = logging.getLogger(__name__)


# =============================================================================
# CategoryAmeliorator
# =============================================================================


class CategoryAmeliorator:
    """
    Gestionnaire d'amélioration incrémentale des catégories.

    Cette classe permet de:
    1. Assigner de nouvelles notes aux catégories existantes (K-NN)
    2. Raffiner les catégories (recalcul centroides, mises à jour)
    3. Suggérer des sous-catégories (clustering intra-catégorie)
    4. Suggérer des fusions (catégories trop similaires)
    5. Orchestrer l'amélioration complète

    Attributes:
        category_store: Store pour charger/sauvegarder taxonomie
        embedding_manager: Manager pour générer embeddings
        ollama_client: Client Ollama pour LLM
        confidence_threshold: Seuil minimum de confiance
        min_notes_per_category: Nombre minimum de notes par catégorie
    """

    def __init__(
        self,
        category_store: Optional[CategoryStore] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        ollama_client: Optional[OllamaClient] = None,
        confidence_threshold: float = 0.7,
        min_notes_per_category: int = 5,
    ):
        """
        Initialise le CategoryAmeliorator.

        Args:
            category_store: Store de catégories (créé si None)
            embedding_manager: Manager d'embeddings (créé si None)
            ollama_client: Client Ollama (créé si None)
            confidence_threshold: Seuil de confiance pour assignation (0-1)
            min_notes_per_category: Nombre minimum de notes par catégorie
        """
        self.category_store = category_store or CategoryStore()
        self.ollama_client = ollama_client or OllamaClient()
        self.embedding_manager = embedding_manager or EmbeddingManager(
            ollama_client=self.ollama_client
        )

        self.confidence_threshold = confidence_threshold
        self.min_notes_per_category = min_notes_per_category

        logger.info(
            f"CategoryAmeliorator initialisé - "
            f"threshold={confidence_threshold}, "
            f"min_notes={min_notes_per_category}"
        )

    def load_existing_taxonomy(self) -> List[Category]:
        """
        Charge la taxonomie existante depuis le CategoryStore.

        Returns:
            List[Category]: Liste des catégories existantes

        Raises:
            ValueError: Si aucune taxonomie n'existe
        """
        logger.info("Chargement de la taxonomie existante")

        categories = self.category_store.load_taxonomy()

        if not categories:
            raise ValueError(
                "Aucune taxonomie existante trouvée. "
                "Lancez d'abord 'obsillama analyze' pour créer des catégories."
            )

        # Filtrer uniquement les catégories approuvées
        approved_categories = [
            cat for cat in categories if cat.review_status == ReviewStatus.APPROVED
        ]

        logger.info(
            f"Taxonomie chargée: {len(categories)} catégories totales, "
            f"{len(approved_categories)} approuvées"
        )

        return approved_categories

    def assign_new_notes(
        self,
        new_notes: List[Note],
        existing_categories: List[Category],
        note_embeddings: List[List[float]],
        category_embeddings: List[List[float]],
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Assigne les nouvelles notes aux catégories existantes via K-NN.

        Utilise la similarité cosinus entre les embeddings des notes et
        les embeddings (centroides) des catégories pour l'assignation.

        Args:
            new_notes: Nouvelles notes à assigner
            existing_categories: Catégories existantes
            note_embeddings: Embeddings des nouvelles notes
            category_embeddings: Embeddings (centroides) des catégories

        Returns:
            Dict[str, List[Tuple[str, float]]]: Assignations
                {category_id: [(note_id, confidence_score), ...]}

        Raises:
            ValueError: Si mismatch entre notes/embeddings
        """
        logger.info(
            f"Assignation de {len(new_notes)} nouvelles notes à "
            f"{len(existing_categories)} catégories"
        )

        if len(new_notes) != len(note_embeddings):
            raise ValueError(
                f"Mismatch: {len(new_notes)} notes vs {len(note_embeddings)} embeddings"
            )

        if len(existing_categories) != len(category_embeddings):
            raise ValueError(
                f"Mismatch: {len(existing_categories)} catégories vs "
                f"{len(category_embeddings)} embeddings"
            )

        # Dictionnaire des assignations
        assignments: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        # Pour chaque nouvelle note, trouver la meilleure catégorie (K-NN avec K=1)
        assigned_count = 0

        for note, note_emb in zip(new_notes, note_embeddings):
            best_category_id = None
            best_similarity = 0.0

            # Calculer similarité avec toutes les catégories
            for category, cat_emb in zip(existing_categories, category_embeddings):
                similarity = cosine_similarity(note_emb, cat_emb)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_category_id = category.id

            # Assigner si au-dessus du seuil
            if best_category_id and best_similarity >= self.confidence_threshold:
                assignments[best_category_id].append((note.id, best_similarity))
                assigned_count += 1
                logger.debug(
                    f"Note '{note.title}' → Catégorie (confidence={best_similarity:.2f})"
                )
            else:
                logger.debug(
                    f"Note '{note.title}' non assignée (max_similarity={best_similarity:.2f})"
                )

        # Statistiques
        coverage = (assigned_count / len(new_notes) * 100) if new_notes else 0
        logger.info(
            f"Assignation terminée: {assigned_count}/{len(new_notes)} notes "
            f"assignées ({coverage:.1f}% couverture)"
        )
        logger.info(f"  → {len(assignments)} catégories ont reçu des notes")

        return assignments

    def refine_categories(
        self,
        all_notes: List[Note],
        categories: List[Category],
        note_embeddings: List[List[float]],
        assignments: Dict[str, List[Tuple[str, float]]],
    ) -> List[Category]:
        """
        Raffine les catégories existantes en recalculant leurs centroides.

        Met à jour:
        - Centroides (embedding moyen des notes de la catégorie)
        - note_count
        - avg_confidence

        Args:
            all_notes: Toutes les notes (anciennes + nouvelles)
            categories: Catégories à raffiner
            note_embeddings: Embeddings de toutes les notes
            assignments: Assignations actuelles

        Returns:
            List[Category]: Catégories raffinées
        """
        logger.info(f"Raffinement de {len(categories)} catégories")

        # Créer un mapping note_id → embedding
        note_id_to_embedding = {}
        note_id_to_note = {}

        for note, emb in zip(all_notes, note_embeddings):
            note_id_to_embedding[note.id] = emb
            note_id_to_note[note.id] = note

        # Pour chaque catégorie, recalculer le centroide
        refined_categories = []

        for category in categories:
            if category.id not in assignments:
                # Aucune note assignée, garder tel quel
                refined_categories.append(category)
                continue

            assigned_notes = assignments[category.id]

            # Extraire les embeddings des notes de cette catégorie
            category_note_embeddings = []
            confidences = []

            for note_id, confidence in assigned_notes:
                if note_id in note_id_to_embedding:
                    category_note_embeddings.append(note_id_to_embedding[note_id])
                    confidences.append(confidence)

            if not category_note_embeddings:
                refined_categories.append(category)
                continue

            # Recalculer le centroide (moyenne des embeddings)
            centroid = np.mean(category_note_embeddings, axis=0).tolist()

            # Mettre à jour les statistiques
            category.note_count = len(assigned_notes)
            category.avg_confidence = np.mean(confidences) if confidences else 0.0

            # Note: On ne stocke pas le centroide dans Category pour l'instant
            # Il sera recalculé à la demande via EmbeddingStore.get_category_centroid()

            logger.debug(
                f"Catégorie '{category.name}': {category.note_count} notes, "
                f"avg_confidence={category.avg_confidence:.2f}"
            )

            refined_categories.append(category)

        logger.info("Raffinement terminé")

        return refined_categories

    def suggest_subcategories(
        self,
        category: Category,
        assigned_notes: List[Note],
        note_embeddings: List[List[float]],
        max_subcategories: int = 5,
        min_notes_per_subcat: int = 10,
    ) -> List[Category]:
        """
        Suggère des sous-catégories via clustering intra-catégorie.

        Utilise K-Means pour grouper les notes d'une catégorie et
        crée des sous-catégories suggérées.

        Args:
            category: Catégorie parente
            assigned_notes: Notes assignées à cette catégorie
            note_embeddings: Embeddings de ces notes
            max_subcategories: Nombre maximum de sous-catégories
            min_notes_per_subcat: Nombre minimum de notes par sous-catégorie

        Returns:
            List[Category]: Sous-catégories suggérées
        """
        logger.info(
            f"Suggestion de sous-catégories pour '{category.name}' "
            f"({len(assigned_notes)} notes)"
        )

        if len(assigned_notes) < min_notes_per_subcat * 2:
            logger.info(
                f"  → Trop peu de notes ({len(assigned_notes)}), "
                f"pas de sous-catégories suggérées"
            )
            return []

        # Déterminer le nombre optimal de clusters
        n_clusters = min(
            max_subcategories,
            len(assigned_notes) // min_notes_per_subcat
        )

        if n_clusters < 2:
            logger.info("  → Pas assez de notes pour créer des sous-catégories")
            return []

        try:
            # Clustering K-Means
            logger.debug(f"  → Clustering avec {n_clusters} clusters")
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(note_embeddings)

            # Créer des sous-catégories basées sur les clusters
            subcategories = []

            for cluster_id in range(n_clusters):
                cluster_notes = [
                    note
                    for note, label in zip(assigned_notes, cluster_labels)
                    if label == cluster_id
                ]

                if len(cluster_notes) < min_notes_per_subcat:
                    continue

                # Générer un nom de sous-catégorie simple
                subcat_name = f"{category.name} - Groupe {cluster_id + 1}"
                subcat_id = generate_category_id(subcat_name)

                # Créer la sous-catégorie
                subcategory = Category(
                    id=subcat_id,
                    name=subcat_name,
                    description=f"Sous-catégorie de {category.name}",
                    tag_name=f"AI-Category-{category.name.replace(' ', '-')}-{cluster_id + 1}",
                    keywords=category.keywords,
                    note_count=len(cluster_notes),
                    avg_confidence=0.8,
                    review_status=ReviewStatus.PENDING,
                    parent_id=category.id,
                    children_ids=[],
                    level=category.level + 1,
                )

                subcategories.append(subcategory)

            logger.info(f"  → {len(subcategories)} sous-catégories suggérées")

            return subcategories

        except Exception as e:
            logger.error(f"Erreur lors du clustering: {e}")
            return []

    def suggest_merges(
        self,
        categories: List[Category],
        category_embeddings: List[List[float]],
        similarity_threshold: float = 0.85,
    ) -> List[Tuple[str, str, float]]:
        """
        Suggère des fusions de catégories trop similaires.

        Identifie les paires de catégories avec une similarité élevée
        qui pourraient être fusionnées.

        Args:
            categories: Liste des catégories
            category_embeddings: Embeddings (centroides) des catégories
            similarity_threshold: Seuil de similarité pour suggérer fusion (0-1)

        Returns:
            List[Tuple[str, str, float]]: Suggestions de fusion
                [(cat1_id, cat2_id, similarity_score), ...]
        """
        logger.info(
            f"Recherche de fusions potentielles parmi {len(categories)} catégories "
            f"(seuil={similarity_threshold})"
        )

        if len(categories) != len(category_embeddings):
            raise ValueError(
                f"Mismatch: {len(categories)} catégories vs "
                f"{len(category_embeddings)} embeddings"
            )

        merge_suggestions = []

        # Comparer toutes les paires de catégories
        for i, (cat1, emb1) in enumerate(zip(categories, category_embeddings)):
            for j, (cat2, emb2) in enumerate(zip(categories[i + 1:], category_embeddings[i + 1:]), start=i + 1):
                # Calculer la similarité
                similarity = cosine_similarity(emb1, emb2)

                if similarity >= similarity_threshold:
                    merge_suggestions.append((cat1.id, cat2.id, similarity))
                    logger.debug(
                        f"Fusion suggérée: '{cat1.name}' + '{cat2.name}' "
                        f"(similarity={similarity:.2f})"
                    )

        logger.info(f"  → {len(merge_suggestions)} fusions suggérées")

        return merge_suggestions

    def run_amelioration(
        self,
        new_notes: List[Note],
        suggest_subcats: bool = True,
        suggest_fusions: bool = True,
        merge_threshold: float = 0.85,
    ) -> Dict[str, any]:
        """
        Orchestre l'amélioration complète de la taxonomie.

        Workflow:
        1. Charger la taxonomie existante
        2. Générer embeddings pour nouvelles notes et catégories
        3. Assigner nouvelles notes aux catégories (K-NN)
        4. Raffiner les catégories (recalcul centroides)
        5. Suggérer sous-catégories (optionnel)
        6. Suggérer fusions (optionnel)
        7. Sauvegarder les mises à jour

        Args:
            new_notes: Nouvelles notes à traiter
            suggest_subcats: Suggérer des sous-catégories?
            suggest_fusions: Suggérer des fusions?
            merge_threshold: Seuil pour suggestions de fusion

        Returns:
            Dict: Résumé de l'amélioration avec statistiques et suggestions
        """
        logger.info(f"Démarrage de l'amélioration avec {len(new_notes)} nouvelles notes")

        # 1. Charger taxonomie existante
        existing_categories = self.load_existing_taxonomy()

        # 2. Générer embeddings pour nouvelles notes
        logger.info("Génération des embeddings pour les nouvelles notes...")
        # Extraire textes des notes
        note_texts = [f"{note.title}\n\n{note.content}" for note in new_notes]
        # Générer embeddings
        new_note_embeddings = self.embedding_manager.generate_embeddings_batch(
            note_texts
        )

        # 3. Générer embeddings pour catégories (description)
        logger.info("Génération des embeddings pour les catégories...")
        category_texts = [
            f"{cat.name}: {cat.description}" for cat in existing_categories
        ]
        category_embeddings = self.embedding_manager.generate_embeddings_batch(
            category_texts
        )

        # 4. Assigner nouvelles notes aux catégories
        logger.info("Assignation des nouvelles notes...")
        assignments = self.assign_new_notes(
            new_notes=new_notes,
            existing_categories=existing_categories,
            note_embeddings=new_note_embeddings,
            category_embeddings=category_embeddings,
        )

        # 5. Raffiner les catégories
        logger.info("Raffinement des catégories...")
        refined_categories = self.refine_categories(
            all_notes=new_notes,
            categories=existing_categories,
            note_embeddings=new_note_embeddings,
            assignments=assignments,
        )

        # 6. Suggestions de sous-catégories
        subcategory_suggestions = []

        if suggest_subcats:
            logger.info("Suggestion de sous-catégories...")

            # Créer mapping note_id → Note
            note_id_to_note = {note.id: note for note in new_notes}
            note_id_to_emb = {
                note.id: emb
                for note, emb in zip(new_notes, new_note_embeddings)
            }

            for category in refined_categories:
                if category.id in assignments:
                    assigned_note_ids = [
                        note_id for note_id, _ in assignments[category.id]
                    ]
                    assigned_notes = [
                        note_id_to_note[nid]
                        for nid in assigned_note_ids
                        if nid in note_id_to_note
                    ]
                    assigned_embeddings = [
                        note_id_to_emb[nid]
                        for nid in assigned_note_ids
                        if nid in note_id_to_emb
                    ]

                    subcats = self.suggest_subcategories(
                        category=category,
                        assigned_notes=assigned_notes,
                        note_embeddings=assigned_embeddings,
                    )

                    subcategory_suggestions.extend(subcats)

        # 7. Suggestions de fusions
        merge_suggestions = []

        if suggest_fusions:
            logger.info("Suggestion de fusions...")
            merge_suggestions = self.suggest_merges(
                categories=refined_categories,
                category_embeddings=category_embeddings,
                similarity_threshold=merge_threshold,
            )

        # 8. Sauvegarder les mises à jour
        logger.info("Sauvegarde de la taxonomie raffinée...")
        self.category_store.save_taxonomy(refined_categories)

        logger.info("Sauvegarde des assignations...")
        self.category_store.save_assignments(assignments)

        # Préparer le résumé
        total_assigned = sum(len(notes) for notes in assignments.values())
        coverage = (total_assigned / len(new_notes) * 100) if new_notes else 0

        result = {
            "new_notes_count": len(new_notes),
            "assigned_notes_count": total_assigned,
            "coverage_percent": coverage,
            "categories_count": len(refined_categories),
            "categories_with_new_notes": len(assignments),
            "subcategory_suggestions": subcategory_suggestions,
            "merge_suggestions": merge_suggestions,
            "assignments": assignments,
        }

        logger.info("Amélioration terminée ✓")

        return result
