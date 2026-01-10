"""
ObsIllama - Category Generator

Ce module génère des catégories à partir des communautés GraphRAG détectées.
Il mappe les communautés vers des catégories thématiques et assigne les notes.
"""

import logging
import hashlib
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans

from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.prompts.categorization import (
    get_category_generation_prompt,
    get_category_naming_prompt,
    get_subcategory_suggestion_prompt,
)
from obsillama.models.note import Note
from obsillama.models.category import Category, ReviewStatus
from obsillama.models.graph_entity import GraphEntity, GraphCommunity
from obsillama.llm.graphrag_integration import safe_json_parse

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def generate_category_id(name: str) -> str:
    """
    Génère un ID unique pour une catégorie basé sur son nom.

    Args:
        name: Nom de la catégorie

    Returns:
        ID unique (hash)
    """
    normalized = name.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs.

    Args:
        vec1: Premier vecteur
        vec2: Deuxième vecteur

    Returns:
        Score de similarité (0-1)
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return float(dot_product / (norm_v1 * norm_v2))


# =============================================================================
# CategoryGenerator
# =============================================================================


class CategoryGenerator:
    """
    Générateur de catégories à partir de communautés GraphRAG.

    Ce générateur :
    1. Transforme les communautés en catégories thématiques
    2. Génère des noms et descriptions via LLM
    3. Assigne les notes aux catégories basé sur les embeddings
    4. Construit une hiérarchie parent-enfant
    5. Génère des tag names pour Obsidian
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        target_category_count: int = 20,
        min_notes_per_category: int = 5,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialise le générateur de catégories.

        Args:
            ollama_client: Client Ollama pour appels LLM
            target_category_count: Nombre de catégories cibles
            min_notes_per_category: Minimum de notes par catégorie
            confidence_threshold: Seuil de confiance pour assignation
        """
        self.client = ollama_client
        self.target_category_count = target_category_count
        self.min_notes_per_category = min_notes_per_category
        self.confidence_threshold = confidence_threshold

        logger.info(
            f"CategoryGenerator initialisé "
            f"(target={target_category_count}, "
            f"min_notes={min_notes_per_category}, "
            f"threshold={confidence_threshold})"
        )

    def generate_from_communities(
        self,
        communities: List[GraphCommunity],
        entities: List[GraphEntity],
    ) -> List[Category]:
        """
        Génère des catégories à partir des communautés GraphRAG.

        Args:
            communities: Liste des communautés détectées
            entities: Liste de toutes les entités (pour récupérer les infos)

        Returns:
            Liste des catégories générées
        """
        logger.info(
            f"Génération de catégories depuis {len(communities)} communautés"
        )

        if not communities:
            logger.warning("Aucune communauté fournie, retour liste vide")
            return []

        categories = []

        for community in communities:
            try:
                # Récupérer les entités de cette communauté
                community_entities = [
                    e for e in entities if e.id in community.entity_ids
                ]

                if not community_entities:
                    continue

                # Générer la catégorie via LLM
                category = self._generate_category_from_community(
                    community, community_entities
                )

                if category:
                    categories.append(category)

            except Exception as e:
                logger.error(
                    f"Erreur génération catégorie depuis communauté {community.id} : {e}"
                )
                continue

        logger.info(f"  → {len(categories)} catégories générées")
        return categories

    def _generate_category_from_community(
        self,
        community: GraphCommunity,
        entities: List[GraphEntity],
    ) -> Optional[Category]:
        """
        Génère une catégorie depuis une communauté.

        Args:
            community: Communauté GraphRAG
            entities: Entités de la communauté

        Returns:
            Catégorie générée ou None
        """
        logger.debug(f"Génération catégorie pour communauté {community.id}")

        # Préparer les données pour le prompt
        entity_names = [e.name for e in entities[:20]]
        community_summary = community.description or f"Communauté {community.id}"

        # Construire le prompt
        prompt = get_category_generation_prompt(entity_names, community_summary)

        # Appeler le LLM
        try:
            response = self.client.generate(prompt)
        except Exception as e:
            logger.error(f"Erreur appel LLM : {e}")
            return None

        # Parser la réponse JSON
        parsed = safe_json_parse(response, {})

        if not parsed or "name" not in parsed:
            logger.warning(f"Réponse LLM invalide : {response[:200]}")
            return None

        # Créer la catégorie
        category_name = parsed.get("name", f"Catégorie {community.id}")
        category_id = generate_category_id(category_name)

        category = Category(
            id=category_id,
            name=category_name,
            description=parsed.get("description", ""),
            keywords=parsed.get("keywords", []),
            tag_name=self._generate_tag_name(category_name),
            note_count=0,  # Sera mis à jour lors de l'assignation
            avg_confidence=parsed.get("confidence", 0.8),
            review_status=ReviewStatus.PENDING,
            parent_id=None,
            children_ids=[],
            level=0,
        )

        logger.debug(f"  → Catégorie créée : {category.name}")
        return category

    def _generate_tag_name(self, category_name: str) -> str:
        """
        Génère un tag name Obsidian depuis un nom de catégorie.

        Args:
            category_name: Nom de la catégorie

        Returns:
            Tag name (ex: "AI-Category-Python")
        """
        # Normaliser : enlever accents, espaces, caractères spéciaux
        normalized = category_name.strip()
        normalized = normalized.replace(" ", "-")
        normalized = normalized.replace("'", "")
        normalized = normalized.replace('"', "")

        return f"AI-Category-{normalized}"

    def assign_notes_to_categories(
        self,
        notes: List[Note],
        categories: List[Category],
        note_embeddings: List[List[float]],
        category_embeddings: List[List[float]],
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Assigne les notes aux catégories basé sur la similarité des embeddings.

        Args:
            notes: Liste des notes
            categories: Liste des catégories
            note_embeddings: Embeddings des notes
            category_embeddings: Embeddings des catégories

        Returns:
            Dictionnaire {category_id: [(note_id, confidence), ...]}
        """
        logger.info(
            f"Assignation de {len(notes)} notes à {len(categories)} catégories"
        )

        if len(notes) != len(note_embeddings):
            raise ValueError(
                f"Mismatch: {len(notes)} notes vs {len(note_embeddings)} embeddings"
            )

        if len(categories) != len(category_embeddings):
            raise ValueError(
                f"Mismatch: {len(categories)} catégories vs {len(category_embeddings)} embeddings"
            )

        # Dictionnaire des assignations
        assignments: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        # Pour chaque note, trouver la meilleure catégorie
        for note, note_emb in zip(notes, note_embeddings):
            best_category_id = None
            best_similarity = 0.0

            for category, cat_emb in zip(categories, category_embeddings):
                similarity = cosine_similarity(note_emb, cat_emb)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_category_id = category.id

            # Assigner si au-dessus du seuil
            if best_category_id and best_similarity >= self.confidence_threshold:
                assignments[best_category_id].append((note.id, best_similarity))

        # Mettre à jour les note_count et avg_confidence
        for category in categories:
            if category.id in assignments:
                notes_assigned = assignments[category.id]
                category.note_count = len(notes_assigned)
                category.avg_confidence = sum(
                    conf for _, conf in notes_assigned
                ) / len(notes_assigned)

        # Filtrer les catégories trop petites
        assignments_filtered = {
            cat_id: notes_list
            for cat_id, notes_list in assignments.items()
            if len(notes_list) >= self.min_notes_per_category
        }

        logger.info(
            f"  → {len(assignments_filtered)} catégories ont des notes assignées"
        )
        logger.info(
            f"  → {sum(len(v) for v in assignments_filtered.values())} notes assignées au total"
        )

        return assignments_filtered

    def build_hierarchy(self, categories: List[Category]) -> List[Category]:
        """
        Construit une hiérarchie parent-enfant entre les catégories.

        Cette méthode utilise un clustering simple pour regrouper les catégories
        similaires sous des catégories parentes.

        Args:
            categories: Liste des catégories (plate)

        Returns:
            Liste des catégories avec hiérarchie mise à jour
        """
        logger.info(f"Construction de la hiérarchie pour {len(categories)} catégories")

        if len(categories) < 3:
            logger.info("  → Pas assez de catégories pour une hiérarchie")
            return categories

        # Pour l'instant, retourner les catégories telles quelles (niveau 0)
        # TODO: Implémenter un vrai clustering hiérarchique si besoin
        for category in categories:
            category.level = 0
            category.parent_id = None
            category.children_ids = []

        logger.info("  → Hiérarchie plate (niveau 0)")
        return categories

    def suggest_subcategories(
        self,
        parent_category: Category,
        notes: List[Note],
        note_embeddings: List[List[float]],
        min_notes_per_subcat: int = 5,
    ) -> List[Category]:
        """
        Suggère des sous-catégories pour une catégorie trop large.

        Args:
            parent_category: Catégorie parente
            notes: Notes assignées à cette catégorie
            note_embeddings: Embeddings des notes
            min_notes_per_subcat: Minimum de notes par sous-catégorie

        Returns:
            Liste des sous-catégories suggérées
        """
        logger.info(
            f"Suggestion de sous-catégories pour '{parent_category.name}' "
            f"({len(notes)} notes)"
        )

        if len(notes) < min_notes_per_subcat * 2:
            logger.info("  → Pas assez de notes pour subdiviser")
            return []

        # Clustering K-means pour regrouper les notes
        n_clusters = min(5, len(notes) // min_notes_per_subcat)

        if n_clusters < 2:
            return []

        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(note_embeddings)

            # Créer des sous-catégories basées sur les clusters
            subcategories = []

            for cluster_id in range(n_clusters):
                cluster_notes = [
                    note
                    for note, label in zip(notes, cluster_labels)
                    if label == cluster_id
                ]

                if len(cluster_notes) < min_notes_per_subcat:
                    continue

                # Générer un nom de sous-catégorie simple
                subcat_name = f"{parent_category.name} - Groupe {cluster_id + 1}"
                subcat_id = generate_category_id(subcat_name)

                subcategory = Category(
                    id=subcat_id,
                    name=subcat_name,
                    description=f"Sous-catégorie de {parent_category.name}",
                    keywords=parent_category.keywords,
                    tag_name=self._generate_tag_name(subcat_name),
                    note_count=len(cluster_notes),
                    avg_confidence=0.8,
                    review_status=ReviewStatus.PENDING,
                    parent_id=parent_category.id,
                    children_ids=[],
                    level=parent_category.level + 1,
                )

                subcategories.append(subcategory)

            logger.info(f"  → {len(subcategories)} sous-catégories suggérées")
            return subcategories

        except Exception as e:
            logger.error(f"Erreur lors du clustering : {e}")
            return []

    def generate_tag_names(self, categories: List[Category]) -> List[Category]:
        """
        Génère ou met à jour les tag names pour toutes les catégories.

        Args:
            categories: Liste des catégories

        Returns:
            Liste des catégories avec tag_name mis à jour
        """
        logger.info(f"Génération des tag names pour {len(categories)} catégories")

        for category in categories:
            if not category.tag_name:
                category.tag_name = self._generate_tag_name(category.name)

        return categories
