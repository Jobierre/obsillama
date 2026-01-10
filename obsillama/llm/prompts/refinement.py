"""
Prompts français pour le raffinement et l'amélioration des catégories.

Ce module contient les prompts pour :
- Amélioration de catégories existantes
- Création de sous-catégories
- Fusion de catégories similaires
- Réorganisation de la hiérarchie
"""

from typing import List, Dict, Any


def get_category_improvement_prompt(
    category_name: str,
    category_description: str,
    entities: List[str],
    keywords: List[str],
    note_count: int,
    feedback: str = None
) -> str:
    """
    Génère un prompt pour améliorer une catégorie existante.

    Args:
        category_name: Nom actuel de la catégorie
        category_description: Description actuelle
        entities: Entités associées
        keywords: Mots-clés actuels
        note_count: Nombre de notes
        feedback: Retour utilisateur optionnel

    Returns:
        Prompt formaté pour le LLM
    """
    entities_text = ", ".join(entities[:15])
    keywords_text = ", ".join(keywords)

    feedback_section = ""
    if feedback:
        feedback_section = f"\n\nRETOUR UTILISATEUR :\n{feedback}\n"

    return f"""Tu es un expert en taxonomie et organisation de connaissances.

Voici une catégorie existante qui pourrait être améliorée :

NOM : {category_name}
DESCRIPTION : {category_description}
ENTITÉS PRINCIPALES : {entities_text}
MOTS-CLÉS : {keywords_text}
NOMBRE DE NOTES : {note_count}{feedback_section}

Ta tâche : Analyse cette catégorie et propose des améliorations.

Aspects à considérer :
- Le nom est-il clair et descriptif ?
- La description est-elle précise et informative ?
- Les mots-clés sont-ils pertinents et complets ?
- La catégorie est-elle trop large ou trop spécifique ?
- Y a-t-il des incohérences ?

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "improved_name": "Nom amélioré (ou identique si déjà bon)",
    "improved_description": "Description améliorée",
    "improved_keywords": ["mot-clé1", "mot-clé2", "mot-clé3"],
    "changes_summary": "Résumé des changements apportés (2-3 phrases)",
    "improvement_score": 0.75
}}

Notes :
- improvement_score : score entre 0.0 et 1.0 indiquant l'ampleur des améliorations (0.0 = aucun changement, 1.0 = refonte complète)
- Si aucune amélioration n'est nécessaire, retourne les valeurs identiques avec improvement_score: 0.0
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_subcategory_creation_prompt(
    parent_category: Dict[str, Any],
    entities_clusters: List[Dict[str, Any]],
    min_notes_per_subcat: int = 5
) -> str:
    """
    Génère un prompt pour créer des sous-catégories à partir d'une catégorie large.

    Args:
        parent_category: Informations sur la catégorie parente
        entities_clusters: Clusters d'entités détectés par clustering
        min_notes_per_subcat: Nombre minimum de notes par sous-catégorie

    Returns:
        Prompt formaté pour le LLM
    """
    parent_name = parent_category.get('name', 'Catégorie')
    parent_desc = parent_category.get('description', '')
    note_count = parent_category.get('note_count', 0)

    clusters_text = ""
    for i, cluster in enumerate(entities_clusters[:5], 1):
        entities = ", ".join(cluster.get('entities', [])[:8])
        size = cluster.get('size', 0)
        clusters_text += f"\nCluster {i} ({size} notes) : {entities}"

    return f"""Tu es un expert en organisation hiérarchique et taxonomie.

Voici une catégorie qui contient {note_count} notes et plusieurs clusters d'entités :

CATÉGORIE PARENTE : {parent_name}
DESCRIPTION : {parent_desc}

CLUSTERS DÉTECTÉS :{clusters_text}

Ta tâche : Propose une division en sous-catégories logiques et cohérentes.

Critères pour créer des sous-catégories :
- Chaque sous-catégorie doit avoir au moins {min_notes_per_subcat} notes
- Les sous-catégories doivent être thématiquement distinctes
- Les noms doivent être clairs et descriptifs
- L'ensemble doit former une hiérarchie logique

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "subcategories": [
        {{
            "name": "Nom de la sous-catégorie",
            "description": "Description de la sous-catégorie",
            "keywords": ["mot-clé1", "mot-clé2"],
            "expected_note_count": 10,
            "cluster_ids": [0, 2]
        }}
    ],
    "reasoning": "Explication de la logique de division (2-3 phrases)"
}}

Notes :
- cluster_ids : indices des clusters qui appartiennent à cette sous-catégorie
- Si aucune division n'est pertinente, retourne {{"subcategories": [], "reasoning": "..."}}
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_category_merge_prompt(categories: List[Dict[str, Any]], similarity_threshold: float = 0.85) -> str:
    """
    Génère un prompt pour identifier les catégories à fusionner.

    Args:
        categories: Liste des catégories à analyser
        similarity_threshold: Seuil de similarité pour suggérer une fusion

    Returns:
        Prompt formaté pour le LLM
    """
    categories_text = ""
    for i, cat in enumerate(categories[:20], 1):
        name = cat.get('name', f'Catégorie {i}')
        desc = cat.get('description', '')[:100]
        keywords = ", ".join(cat.get('keywords', [])[:5])
        note_count = cat.get('note_count', 0)

        categories_text += f"\n{i}. {name} ({note_count} notes)"
        categories_text += f"\n   Description : {desc}"
        categories_text += f"\n   Mots-clés : {keywords}\n"

    return f"""Tu es un expert en taxonomie et normalisation de catégories.

Voici une liste de catégories existantes :
{categories_text}

Ta tâche : Identifie les catégories qui sont trop similaires et qui devraient être fusionnées.

Critères pour fusionner des catégories :
- Elles couvrent des thèmes très proches ou identiques
- Leurs mots-clés se chevauchent significativement
- Fusionner améliorerait la cohérence globale
- La catégorie fusionnée resterait cohérente et bien définie

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "merges": [
        {{
            "category_ids": [2, 5],
            "category_names": ["Nom catégorie 2", "Nom catégorie 5"],
            "merged_name": "Nom de la catégorie fusionnée",
            "merged_description": "Description de la catégorie fusionnée",
            "merged_keywords": ["mot-clé1", "mot-clé2"],
            "reasoning": "Pourquoi fusionner ces catégories (1-2 phrases)"
        }}
    ]
}}

Notes :
- category_ids : indices des catégories à fusionner (commence à 1)
- Si aucune fusion n'est nécessaire, retourne {{"merges": []}}
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_hierarchy_reorganization_prompt(categories: List[Dict[str, Any]]) -> str:
    """
    Génère un prompt pour réorganiser la hiérarchie des catégories.

    Args:
        categories: Liste de toutes les catégories (plates)

    Returns:
        Prompt formaté pour le LLM
    """
    categories_text = ""
    for i, cat in enumerate(categories[:30], 1):
        name = cat.get('name', f'Catégorie {i}')
        keywords = ", ".join(cat.get('keywords', [])[:4])
        note_count = cat.get('note_count', 0)

        categories_text += f"\n{i}. {name} ({note_count} notes) - {keywords}"

    return f"""Tu es un expert en architecture de l'information et organisation hiérarchique.

Voici une liste plate de catégories :
{categories_text}

Ta tâche : Propose une organisation hiérarchique logique (parent-enfant).

Critères pour créer une hiérarchie :
- Les catégories générales deviennent des parents
- Les catégories spécifiques deviennent des enfants
- La hiérarchie doit avoir 2-3 niveaux maximum
- Les regroupements doivent être naturels et intuitifs

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "hierarchy": [
        {{
            "parent_id": 1,
            "parent_name": "Développement",
            "children_ids": [3, 7, 12],
            "children_names": ["Python", "JavaScript", "DevOps"],
            "reasoning": "Technologies et pratiques de développement"
        }}
    ],
    "orphans": [2, 5],
    "orphans_reasoning": "Catégories qui ne rentrent pas dans une hiérarchie claire"
}}

Notes :
- parent_id/children_ids : indices des catégories (commence à 1)
- orphans : catégories qui restent au niveau racine
- Si aucune hiérarchie n'est nécessaire, retourne {{"hierarchy": [], "orphans": [1, 2, 3, ...]}}
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_category_quality_assessment_prompt(category: Dict[str, Any]) -> str:
    """
    Génère un prompt pour évaluer la qualité d'une catégorie.

    Args:
        category: Informations sur la catégorie

    Returns:
        Prompt formaté pour le LLM
    """
    name = category.get('name', '')
    description = category.get('description', '')
    keywords = ", ".join(category.get('keywords', []))
    note_count = category.get('note_count', 0)
    entities = ", ".join(category.get('entities', [])[:10])

    return f"""Tu es un expert en évaluation de la qualité de taxonomies.

Voici une catégorie à évaluer :

NOM : {name}
DESCRIPTION : {description}
MOTS-CLÉS : {keywords}
NOMBRE DE NOTES : {note_count}
ENTITÉS PRINCIPALES : {entities}

Ta tâche : Évalue la qualité de cette catégorie selon plusieurs critères.

Critères d'évaluation :
1. Clarté du nom (0-1) : Le nom est-il clair et descriptif ?
2. Pertinence de la description (0-1) : La description est-elle informative ?
3. Cohérence des mots-clés (0-1) : Les mots-clés sont-ils pertinents ?
4. Taille appropriée (0-1) : Le nombre de notes est-il adapté ?
5. Cohérence thématique (0-1) : Les entités forment-elles un thème cohérent ?

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "scores": {{
        "name_clarity": 0.9,
        "description_relevance": 0.85,
        "keywords_coherence": 0.8,
        "size_appropriateness": 0.7,
        "thematic_coherence": 0.95
    }},
    "overall_quality": 0.84,
    "strengths": ["Point fort 1", "Point fort 2"],
    "weaknesses": ["Point faible 1", "Point faible 2"],
    "recommendations": ["Recommandation 1", "Recommandation 2"]
}}

Notes :
- overall_quality : moyenne des 5 scores
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""
