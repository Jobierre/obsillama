"""
Prompts français pour l'analyse GraphRAG des notes Obsidian.

Ce module contient les prompts pour :
- Extraction d'entités (personnes, technologies, concepts, etc.)
- Extraction de relations entre entités
- Génération de résumés de communautés
"""

from typing import List, Dict, Any


def get_entity_extraction_prompt(note_title: str, note_content: str, max_entities: int = 20) -> str:
    """
    Génère un prompt pour extraire les entités principales d'une note.

    Les entités sont les concepts, technologies, personnes, lieux, organisations, etc.
    mentionnés dans la note.

    Args:
        note_title: Titre de la note
        note_content: Contenu de la note (texte markdown)
        max_entities: Nombre maximum d'entités à extraire

    Returns:
        Prompt formaté pour le LLM
    """
    # Limiter le contenu pour éviter des prompts trop longs
    content_preview = note_content[:2000]
    if len(note_content) > 2000:
        content_preview += "\n\n[...contenu tronqué...]"

    return f"""Tu es un expert en extraction d'informations et analyse de texte.

Voici une note Obsidian à analyser :

TITRE : {note_title}

CONTENU :
{content_preview}

Ta tâche : Identifie et extrait les entités principales mentionnées dans cette note.

Types d'entités à extraire :
- TECHNOLOGY : Technologies, langages, frameworks, outils (ex: Python, Docker, React)
- CONCEPT : Concepts, idées, théories, méthodes (ex: Machine Learning, DevOps, GraphRAG)
- PERSON : Personnes, auteurs, experts (ex: Linus Torvalds, Einstein)
- ORGANIZATION : Entreprises, institutions, projets (ex: Google, MIT, Linux Foundation)
- LOCATION : Lieux, pays, villes (ex: Paris, Silicon Valley)
- PRODUCT : Produits, services, applications (ex: ChatGPT, Kubernetes)
- EVENT : Événements, conférences (ex: WWDC, PyCon)
- OTHER : Autres entités importantes

Règles d'extraction :
- Extrais jusqu'à {max_entities} entités maximum
- Privilégie les entités les plus importantes et les plus mentionnées
- Normalise les noms (ex: "python" → "Python", "k8s" → "Kubernetes")
- Évite les mots trop génériques (ex: "chose", "truc")
- Inclus une brève description pour chaque entité

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "entities": [
        {{
            "name": "Python",
            "type": "TECHNOLOGY",
            "description": "Langage de programmation de haut niveau",
            "importance": 0.9
        }},
        {{
            "name": "Machine Learning",
            "type": "CONCEPT",
            "description": "Domaine de l'IA permettant aux systèmes d'apprendre",
            "importance": 0.85
        }}
    ]
}}

Notes :
- "importance" est un score entre 0.0 et 1.0 indiquant l'importance de l'entité dans la note
- Trie les entités par importance décroissante
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_relationship_extraction_prompt(
    note_title: str,
    note_content: str,
    entities: List[Dict[str, Any]]
) -> str:
    """
    Génère un prompt pour extraire les relations entre entités dans une note.

    Args:
        note_title: Titre de la note
        note_content: Contenu de la note
        entities: Liste des entités déjà extraites

    Returns:
        Prompt formaté pour le LLM
    """
    # Limiter le contenu
    content_preview = note_content[:2000]
    if len(note_content) > 2000:
        content_preview += "\n\n[...contenu tronqué...]"

    # Créer une liste des entités
    entities_list = "\n".join([f"- {e['name']} ({e['type']})" for e in entities[:20]])

    return f"""Tu es un expert en analyse de relations et construction de graphes de connaissances.

Voici une note Obsidian et ses entités extraites :

TITRE : {note_title}

CONTENU :
{content_preview}

ENTITÉS IDENTIFIÉES :
{entities_list}

Ta tâche : Identifie les relations significatives entre ces entités basées sur le contenu de la note.

Types de relations possibles :
- USES : Une technologie/outil utilise une autre (ex: "Docker" USES "Linux")
- IMPLEMENTS : Implémente un concept (ex: "TensorFlow" IMPLEMENTS "Machine Learning")
- RELATED_TO : Relation générale (ex: "Python" RELATED_TO "Data Science")
- PART_OF : Fait partie de (ex: "React" PART_OF "JavaScript")
- CREATED_BY : Créé par (ex: "Linux" CREATED_BY "Linus Torvalds")
- SIMILAR_TO : Similaire à (ex: "Vue" SIMILAR_TO "React")
- REQUIRES : Nécessite (ex: "Django" REQUIRES "Python")

Règles d'extraction :
- Extrais uniquement les relations EXPLICITEMENT mentionnées ou fortement impliquées dans le texte
- Chaque relation doit connecter deux entités de la liste
- Fournis une brève description de la relation
- Indique un score de confiance (0.0 à 1.0)

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "relationships": [
        {{
            "source": "Python",
            "target": "Django",
            "type": "USES",
            "description": "Python est le langage dans lequel Django est écrit",
            "confidence": 0.95
        }},
        {{
            "source": "Machine Learning",
            "target": "TensorFlow",
            "type": "IMPLEMENTS",
            "description": "TensorFlow est un framework pour le Machine Learning",
            "confidence": 0.9
        }}
    ]
}}

Notes :
- Source et target doivent correspondre EXACTEMENT aux noms d'entités de la liste
- Si aucune relation n'est trouvée, retourne "relationships": []
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_community_summary_prompt(
    community_id: int,
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    notes_count: int
) -> str:
    """
    Génère un prompt pour créer un résumé d'une communauté d'entités.

    Une communauté est un groupe d'entités fortement connectées détecté par
    l'algorithme Leiden.

    Args:
        community_id: ID de la communauté
        entities: Entités de la communauté
        relationships: Relations dans la communauté
        notes_count: Nombre de notes contenant ces entités

    Returns:
        Prompt formaté pour le LLM
    """
    # Lister les entités par type
    entities_by_type = {}
    for entity in entities:
        entity_type = entity.get('type', 'OTHER')
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        entities_by_type[entity_type].append(entity['name'])

    entities_text = ""
    for entity_type, names in entities_by_type.items():
        entities_text += f"\n{entity_type} : {', '.join(names[:10])}"
        if len(names) > 10:
            entities_text += f" (et {len(names) - 10} autres)"

    # Lister quelques relations clés
    relationships_text = ""
    for rel in relationships[:10]:
        relationships_text += f"\n- {rel['source']} → {rel['type']} → {rel['target']}"
    if len(relationships) > 10:
        relationships_text += f"\n- ... et {len(relationships) - 10} autres relations"

    return f"""Tu es un expert en synthèse d'information et analyse de graphes de connaissances.

Voici une communauté d'entités fortement connectées, détectée dans un ensemble de notes Obsidian :

COMMUNAUTÉ #{community_id}
Nombre d'entités : {len(entities)}
Nombre de relations : {len(relationships)}
Nombre de notes : {notes_count}

ENTITÉS PAR TYPE :{entities_text}

RELATIONS PRINCIPALES :{relationships_text}

Ta tâche : Rédige un résumé cohérent et informatif de cette communauté.

Le résumé doit :
- Identifier le thème principal ou domaine de connaissance
- Expliquer ce qui lie ces entités entre elles
- Mentionner les concepts, technologies ou sujets clés
- Être clair et concis (3-5 phrases)
- Être en français

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "title": "Titre court de la communauté (3-5 mots)",
    "summary": "Résumé détaillé de la communauté (3-5 phrases)",
    "main_theme": "Thème principal (1 phrase courte)",
    "keywords": ["mot-clé1", "mot-clé2", "mot-clé3", "mot-clé4", "mot-clé5"]
}}

Exemple :
{{
    "title": "Développement Web Frontend",
    "summary": "Cette communauté regroupe les technologies et concepts liés au développement d'interfaces utilisateur web modernes. On y trouve les frameworks JavaScript comme React et Vue, ainsi que les outils de build et les bibliothèques d'interface. Les notes couvrent les bonnes pratiques, les patterns de design et l'architecture frontend.",
    "main_theme": "Technologies et pratiques du développement frontend moderne",
    "keywords": ["React", "JavaScript", "Frontend", "UI/UX", "Components"]
}}

Retourne UNIQUEMENT le JSON, rien d'autre.

JSON :"""


def get_entities_merge_prompt(entities: List[Dict[str, Any]]) -> str:
    """
    Génère un prompt pour identifier et fusionner les entités similaires/dupliquées.

    Args:
        entities: Liste de toutes les entités extraites

    Returns:
        Prompt formaté pour le LLM
    """
    entities_text = "\n".join([
        f"- ID: {i}, Nom: {e['name']}, Type: {e.get('type', 'OTHER')}"
        for i, e in enumerate(entities[:100])  # Limite à 100 pour éviter prompts trop longs
    ])

    return f"""Tu es un expert en normalisation et déduplication de données.

Voici une liste d'entités extraites de plusieurs notes Obsidian :

{entities_text}

Ta tâche : Identifie les entités qui représentent la même chose et qui devraient être fusionnées.

Exemples de doublons à détecter :
- "Python" et "python" → même entité
- "K8s" et "Kubernetes" → même entité
- "ML" et "Machine Learning" → même entité
- "JS" et "JavaScript" → même entité

Règles :
- Propose uniquement des fusions évidentes
- Garde le nom le plus explicite et standard
- Ne fusionne pas des concepts différents même s'ils sont liés

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "merges": [
        {{
            "entity_ids": [2, 15, 23],
            "canonical_name": "Python",
            "reasoning": "Variantes de casse et d'écriture du même langage"
        }}
    ]
}}

Si aucune fusion n'est nécessaire, retourne {{"merges": []}}

Retourne UNIQUEMENT le JSON, rien d'autre.

JSON :"""
