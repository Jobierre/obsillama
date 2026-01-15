"""
ObsIllama - Pipeline GraphRAG

Ce module implémente le pipeline GraphRAG complet pour :
- Extraction d'entités et de relations depuis les notes
- Construction du graphe de connaissances avec igraph
- Détection de communautés avec l'algorithme Leiden
- Génération de résumés de communautés via LLM
"""

import json
import logging
import hashlib
import threading
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import igraph as ig
from tqdm import tqdm

from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.prompts.analysis import (
    get_entity_extraction_prompt,
    get_relationship_extraction_prompt,
    get_community_summary_prompt,
)
from obsillama.models.note import Note
from obsillama.models.graph_entity import (
    GraphEntity,
    GraphRelationship,
    GraphCommunity,
    EntityType,
    RelationshipType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def generate_entity_id(name: str, entity_type: str) -> str:
    """
    Génère un ID unique pour une entité basé sur son nom et type.

    Args:
        name: Nom de l'entité
        entity_type: Type de l'entité

    Returns:
        ID unique (hash)
    """
    normalized = f"{name.lower().strip()}:{entity_type.lower()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def generate_relationship_id(source_id: str, target_id: str, rel_type: str) -> str:
    """
    Génère un ID unique pour une relation.

    Args:
        source_id: ID de l'entité source
        target_id: ID de l'entité cible
        rel_type: Type de relation

    Returns:
        ID unique (hash)
    """
    normalized = f"{source_id}:{rel_type}:{target_id}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def safe_json_parse(text: str, default: Any = None) -> Any:
    """
    Parse JSON de manière sûre avec fallback.

    Args:
        text: Texte à parser
        default: Valeur par défaut en cas d'erreur

    Returns:
        Objet Python parsé ou default
    """
    try:
        # Nettoyer le texte (enlever markdown, espaces, etc.)
        text = text.strip()

        # Enlever les balises markdown si présentes
        if text.startswith("```"):
            lines = text.split("\n")
            # Enlever première ligne (```json)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Enlever dernière ligne (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Parser le JSON
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Échec parsing JSON : {e}. Texte: {text[:200]}")
        return default if default is not None else {}


# =============================================================================
# GraphRAG Pipeline
# =============================================================================


class GraphRAGPipeline:
    """
    Pipeline complet pour l'extraction GraphRAG et la détection de communautés.

    Ce pipeline :
    1. Extrait les entités de chaque note via LLM
    2. Extrait les relations entre entités
    3. Construit un graphe igraph
    4. Détecte des communautés avec Leiden
    5. Génère des résumés de communautés
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        min_community_size: int = 3,
        leiden_resolution: float = 1.0,
        max_entities_per_note: int = 20,
    ):
        """
        Initialise le pipeline GraphRAG.

        Args:
            ollama_client: Client Ollama pour appels LLM
            min_community_size: Taille minimum d'une communauté valide
            leiden_resolution: Paramètre de résolution de Leiden (plus élevé = plus de petites communautés)
            max_entities_per_note: Nombre maximum d'entités à extraire par note
        """
        self.client = ollama_client
        self.min_community_size = min_community_size
        self.leiden_resolution = leiden_resolution
        self.max_entities_per_note = max_entities_per_note

        # Caches
        self.entities_cache: Dict[str, GraphEntity] = {}
        self.relationships_cache: Dict[str, GraphRelationship] = {}

        # Lock pour protéger l'accès concurrent aux caches
        self._cache_lock = threading.Lock()

        logger.info(
            f"GraphRAGPipeline initialisé "
            f"(min_community_size={min_community_size}, "
            f"leiden_resolution={leiden_resolution})"
        )

    def extract_entities(self, note: Note) -> List[GraphEntity]:
        """
        Extrait les entités d'une note via LLM.

        Args:
            note: Note à analyser

        Returns:
            Liste des entités extraites
        """
        logger.debug(f"Extraction entités pour note {note.id} : {note.title}")

        # Construire le prompt
        prompt = get_entity_extraction_prompt(
            note_title=note.title,
            note_content=note.content,
            max_entities=self.max_entities_per_note,
        )

        # Appeler le LLM
        try:
            response = self.client.generate(prompt)
        except Exception as e:
            logger.error(f"Erreur appel LLM pour extraction entités : {e}")
            return []

        # Parser la réponse JSON
        parsed = safe_json_parse(response, {"entities": []})
        entities_data = parsed.get("entities", [])

        if not entities_data:
            logger.warning(f"Aucune entité extraite pour note {note.id}")
            return []

        # Créer les objets GraphEntity
        entities = []
        for entity_data in entities_data:
            try:
                # Générer un ID unique
                entity_name = entity_data.get("name", "").strip()
                entity_type_str = entity_data.get("type", "OTHER").upper()

                if not entity_name:
                    continue

                # Mapper le type string vers l'enum
                try:
                    entity_type = EntityType(entity_type_str.lower())
                except ValueError:
                    entity_type = EntityType.OTHER

                entity_id = generate_entity_id(entity_name, entity_type.value)

                # Vérifier si l'entité existe déjà (protégé par lock pour thread-safety)
                with self._cache_lock:
                    if entity_id in self.entities_cache:
                        entity = self.entities_cache[entity_id]
                        entity.add_mention(note.id)
                    else:
                        # Créer nouvelle entité
                        entity = GraphEntity(
                            id=entity_id,
                            name=entity_name,
                            type=entity_type,
                            description=entity_data.get("description", ""),
                            importance_score=entity_data.get("importance", 0.5),
                            source_note_ids=[note.id],
                            mention_count=1,
                        )
                        self.entities_cache[entity_id] = entity

                entities.append(entity)

            except Exception as e:
                logger.error(f"Erreur création entité : {e}, data={entity_data}")
                continue

        logger.debug(f"  → {len(entities)} entités extraites")
        return entities

    def extract_relationships(
        self, note: Note, entities: List[GraphEntity]
    ) -> List[GraphRelationship]:
        """
        Extrait les relations entre entités dans une note.

        Args:
            note: Note à analyser
            entities: Entités déjà extraites de cette note

        Returns:
            Liste des relations extraites
        """
        if len(entities) < 2:
            logger.debug(f"Note {note.id} : pas assez d'entités pour des relations")
            return []

        logger.debug(f"Extraction relations pour note {note.id}")

        # Préparer les données d'entités pour le prompt
        entities_data = [
            {"name": e.name, "type": e.type.value} for e in entities
        ]

        # Construire le prompt
        prompt = get_relationship_extraction_prompt(
            note_title=note.title,
            note_content=note.content,
            entities=entities_data,
        )

        # Appeler le LLM
        try:
            response = self.client.generate(prompt)
        except Exception as e:
            logger.error(f"Erreur appel LLM pour extraction relations : {e}")
            return []

        # Parser la réponse JSON
        parsed = safe_json_parse(response, {"relationships": []})
        relationships_data = parsed.get("relationships", [])

        if not relationships_data:
            logger.debug(f"Aucune relation extraite pour note {note.id}")
            return []

        # Créer un mapping nom → entity_id
        name_to_id = {e.name: e.id for e in entities}

        # Créer les objets GraphRelationship
        relationships = []
        for rel_data in relationships_data:
            try:
                source_name = rel_data.get("source", "").strip()
                target_name = rel_data.get("target", "").strip()
                rel_type_str = rel_data.get("type", "OTHER").upper()

                # Trouver les IDs des entités
                source_id = name_to_id.get(source_name)
                target_id = name_to_id.get(target_name)

                if not source_id or not target_id:
                    logger.debug(
                        f"Relation ignorée : entités non trouvées "
                        f"({source_name} → {target_name})"
                    )
                    continue

                # Mapper le type
                try:
                    rel_type = RelationshipType(rel_type_str.lower())
                except ValueError:
                    rel_type = RelationshipType.OTHER

                # Générer ID
                rel_id = generate_relationship_id(source_id, target_id, rel_type.value)

                # Vérifier si existe déjà (protégé par lock pour thread-safety)
                with self._cache_lock:
                    if rel_id in self.relationships_cache:
                        relationship = self.relationships_cache[rel_id]
                        relationship.add_evidence(note.id)
                    else:
                        # Créer nouvelle relation
                        relationship = GraphRelationship(
                            id=rel_id,
                            source_entity_id=source_id,
                            target_entity_id=target_id,
                            relationship_type=rel_type,
                            description=rel_data.get("description", ""),
                            confidence=rel_data.get("confidence", 0.8),
                            source_note_ids=[note.id],
                            evidence_count=1,
                        )
                        self.relationships_cache[rel_id] = relationship

                relationships.append(relationship)

            except Exception as e:
                logger.error(f"Erreur création relation : {e}, data={rel_data}")
                continue

        logger.debug(f"  → {len(relationships)} relations extraites")
        return relationships

    def _process_single_note(self, note: Note) -> None:
        """
        Traite une note complète : extraction entités + relations.

        Cette méthode est thread-safe et peut être appelée en parallèle.
        Les résultats sont stockés dans les caches protégés par lock.

        Args:
            note: Note à traiter
        """
        try:
            # Extraire entités
            entities = self.extract_entities(note)

            # Extraire relations si on a des entités
            if entities:
                self.extract_relationships(note, entities)

        except Exception as e:
            logger.error(f"Erreur traitement note {note.id} ({note.title}): {e}")

    def build_graph(
        self, entities: List[GraphEntity], relationships: List[GraphRelationship]
    ) -> ig.Graph:
        """
        Construit un graphe igraph à partir des entités et relations.

        Args:
            entities: Liste des entités (nœuds)
            relationships: Liste des relations (arêtes)

        Returns:
            Graphe igraph
        """
        logger.info(
            f"Construction du graphe : "
            f"{len(entities)} entités, {len(relationships)} relations"
        )

        # Créer un mapping entity_id → vertex index
        entity_id_to_index = {entity.id: i for i, entity in enumerate(entities)}

        # Créer le graphe
        g = ig.Graph(n=len(entities), directed=False)

        # Ajouter les attributs des sommets
        g.vs["id"] = [e.id for e in entities]
        g.vs["name"] = [e.name for e in entities]
        g.vs["type"] = [e.type.value for e in entities]
        g.vs["importance"] = [e.importance_score for e in entities]
        g.vs["mention_count"] = [e.mention_count for e in entities]

        # Ajouter les arêtes
        edges = []
        edge_weights = []
        edge_types = []

        for rel in relationships:
            source_idx = entity_id_to_index.get(rel.source_entity_id)
            target_idx = entity_id_to_index.get(rel.target_entity_id)

            if source_idx is not None and target_idx is not None:
                edges.append((source_idx, target_idx))
                edge_weights.append(rel.weight * rel.confidence)
                edge_types.append(rel.relationship_type.value)

        if edges:
            g.add_edges(edges)
            g.es["weight"] = edge_weights
            g.es["type"] = edge_types

        logger.info(
            f"Graphe construit : "
            f"{g.vcount()} sommets, {g.ecount()} arêtes, "
            f"connecté={g.is_connected()}"
        )

        return g

    def detect_communities(
        self, graph: ig.Graph, entities: List[GraphEntity]
    ) -> List[GraphCommunity]:
        """
        Détecte les communautés dans le graphe avec l'algorithme Leiden.

        Args:
            graph: Graphe igraph
            entities: Liste des entités (pour mapping)

        Returns:
            Liste des communautés détectées
        """
        logger.info("Détection des communautés avec Leiden...")

        if graph.vcount() == 0:
            logger.warning("Graphe vide, aucune communauté à détecter")
            return []

        # Détecter les communautés avec Leiden
        try:
            communities_clustering = graph.community_leiden(
                weights="weight",
                resolution=self.leiden_resolution,
                n_iterations=2,
            )
        except Exception as e:
            logger.error(f"Erreur détection communautés Leiden : {e}")
            return []

        logger.info(
            f"  → {len(communities_clustering)} communautés détectées "
            f"(modularité={communities_clustering.modularity:.3f})"
        )

        # Créer les objets GraphCommunity
        communities = []
        for i, community_members in enumerate(communities_clustering):
            # Filtrer les communautés trop petites
            if len(community_members) < self.min_community_size:
                logger.debug(
                    f"Communauté {i} ignorée (trop petite : {len(community_members)} entités)"
                )
                continue

            # Récupérer les IDs des entités
            entity_ids = [graph.vs[idx]["id"] for idx in community_members]

            # Calculer les stats
            subgraph = graph.subgraph(community_members)
            internal_edges = subgraph.ecount()
            external_edges = sum(
                1
                for idx in community_members
                for neighbor in graph.neighbors(idx)
                if neighbor not in community_members
            )

            # Créer la communauté
            community = GraphCommunity(
                id=f"comm_{i}",
                entity_ids=entity_ids,
                entity_count=len(entity_ids),
                internal_edges=internal_edges,
                external_edges=external_edges,
                modularity=communities_clustering.modularity,
                algorithm="leiden",
                resolution=self.leiden_resolution,
            )

            # Calculer la densité
            community.calculate_density()

            # Identifier les entités les plus importantes (par importance_score)
            community_entities = [e for e in entities if e.id in entity_ids]
            top_entities = sorted(
                community_entities, key=lambda e: e.importance_score, reverse=True
            )[:5]
            community.top_entities = [e.id for e in top_entities]

            communities.append(community)

        logger.info(
            f"  → {len(communities)} communautés valides "
            f"(>= {self.min_community_size} entités)"
        )

        return communities

    def summarize_community(
        self, community: GraphCommunity, entities: List[GraphEntity]
    ) -> str:
        """
        Génère un résumé textuel d'une communauté via LLM.

        Args:
            community: Communauté à résumer
            entities: Toutes les entités (pour récupérer les infos)

        Returns:
            Résumé textuel de la communauté
        """
        logger.debug(f"Génération résumé pour communauté {community.id}")

        # Récupérer les entités de cette communauté
        community_entities = [
            e for e in entities if e.id in community.entity_ids
        ]

        if not community_entities:
            return ""

        # Préparer les données pour le prompt
        entities_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description,
            }
            for e in community_entities
        ]

        # Pour les relations, on devrait les récupérer, mais simplifions pour l'instant
        relationships_data = []

        # Construire le prompt
        prompt = get_community_summary_prompt(
            community_id=int(community.id.split("_")[1]),
            entities=entities_data,
            relationships=relationships_data,
            notes_count=len(set(
                note_id
                for e in community_entities
                for note_id in e.source_note_ids
            )),
        )

        # Appeler le LLM
        try:
            response = self.client.generate(prompt)
        except Exception as e:
            logger.error(f"Erreur appel LLM pour résumé communauté : {e}")
            return ""

        # Parser la réponse JSON
        parsed = safe_json_parse(response, {})

        # Mettre à jour la communauté
        community.name = parsed.get("title", f"Communauté {community.id}")
        community.description = parsed.get("summary", "")
        community.keywords = parsed.get("keywords", [])

        logger.debug(f"  → Résumé généré : {community.name}")

        return community.description

    def run_full_pipeline(
        self, notes: List[Note], show_progress: bool = True
    ) -> Tuple[List[GraphEntity], List[GraphRelationship], List[GraphCommunity]]:
        """
        Exécute le pipeline GraphRAG complet.

        Args:
            notes: Liste des notes à analyser
            show_progress: Afficher une barre de progression

        Returns:
            Tuple (entités, relations, communautés)
        """
        logger.info(f"Démarrage pipeline GraphRAG sur {len(notes)} notes")

        # Réinitialiser les caches
        self.entities_cache = {}
        self.relationships_cache = {}

        # Phase 1 : Extraction entités et relations (parallélisée)
        logger.info("Phase 1/4 : Extraction des entités et relations")

        # Paralléliser l'extraction avec ThreadPoolExecutor (max 10 workers)
        max_workers = min(10, len(notes)) if notes else 1

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre toutes les tâches
            futures = {
                executor.submit(self._process_single_note, note): note
                for note in notes
            }

            # Afficher la progression et récupérer les résultats
            if show_progress and notes:
                pbar = tqdm(total=len(notes), desc="Analyse des notes")
                for future in as_completed(futures):
                    try:
                        future.result()  # Récupère le résultat (ou lève l'exception)
                    except Exception as e:
                        note = futures[future]
                        logger.error(f"Erreur traitement note {note.id}: {e}")
                    pbar.update(1)
                pbar.close()
            else:
                # Sans progress bar, juste attendre la fin
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        note = futures[future]
                        logger.error(f"Erreur traitement note {note.id}: {e}")

        # Récupérer toutes les entités et relations
        all_entities = list(self.entities_cache.values())
        all_relationships = list(self.relationships_cache.values())

        logger.info(
            f"  → {len(all_entities)} entités uniques, "
            f"{len(all_relationships)} relations uniques"
        )

        # Phase 2 : Construction du graphe
        logger.info("Phase 2/4 : Construction du graphe")
        graph = self.build_graph(all_entities, all_relationships)

        # Phase 3 : Détection des communautés
        logger.info("Phase 3/4 : Détection des communautés")
        communities = self.detect_communities(graph, all_entities)

        # Phase 4 : Résumés des communautés
        logger.info("Phase 4/4 : Génération des résumés de communautés")

        # Paralléliser les résumés avec ThreadPoolExecutor (max 5 workers)
        max_workers = min(5, len(communities)) if communities else 1

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre toutes les tâches
            futures = {
                executor.submit(self.summarize_community, community, all_entities): community
                for community in communities
            }

            # Afficher la progression et récupérer les résultats
            if show_progress and communities:
                pbar = tqdm(total=len(communities), desc="Résumés communautés")
                for future in as_completed(futures):
                    try:
                        future.result()  # Récupère le résultat (ou lève l'exception)
                    except Exception as e:
                        community = futures[future]
                        logger.error(f"Erreur résumé communauté {community.id}: {e}")
                    pbar.update(1)
                pbar.close()
            else:
                # Sans progress bar, juste attendre la fin
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        community = futures[future]
                        logger.error(f"Erreur résumé communauté {community.id}: {e}")

        logger.info(
            f"Pipeline GraphRAG terminé : "
            f"{len(all_entities)} entités, "
            f"{len(all_relationships)} relations, "
            f"{len(communities)} communautés"
        )

        return all_entities, all_relationships, communities
