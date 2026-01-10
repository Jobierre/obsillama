"""
Prompts français pour la génération et catégorisation de notes Obsidian.

Ce module contient les prompts utilisés par le LLM pour :
- Générer des catégories à partir de communautés de notes
- Nommer des catégories de manière cohérente
- Créer des descriptions détaillées de catégories
"""

from typing import List


def get_category_generation_prompt(community_entities: List[str], community_summary: str) -> str:
    """
    Génère un prompt pour créer une catégorie à partir d'une communauté d'entités.

    Args:
        community_entities: Liste des noms d'entités dans la communauté
        community_summary: Résumé textuel de la communauté

    Returns:
        Prompt formaté pour le LLM
    """
    entities_text = ", ".join(community_entities[:20])  # Limite à 20 pour éviter prompts trop longs
    if len(community_entities) > 20:
        entities_text += f" (et {len(community_entities) - 20} autres...)"

    return f"""Tu es un assistant spécialisé dans l'organisation de notes Obsidian.

Voici une communauté d'entités extraites de notes qui sont fortement liées entre elles :

Entités principales : {entities_text}

Résumé de la communauté :
{community_summary}

Ta tâche : Suggère une catégorie thématique pour organiser ces notes.

Réponds UNIQUEMENT avec un objet JSON dans ce format exact (sans texte avant ou après) :
{{
    "name": "Nom court et clair de la catégorie (2-4 mots max)",
    "description": "Description détaillée de ce que couvre cette catégorie (1-2 phrases)",
    "keywords": ["mot-clé1", "mot-clé2", "mot-clé3"],
    "confidence": 0.85
}}

Règles importantes :
- Le nom doit être court, clair et en français
- La description doit être informative et précise
- Les keywords doivent capturer les concepts clés
- La confidence doit être entre 0.0 et 1.0 (ta confiance dans cette catégorisation)
- Retourne UNIQUEMENT le JSON, rien d'autre

JSON :"""


def get_category_naming_prompt(entities: List[str], keywords: List[str], current_name: str = None) -> str:
    """
    Génère un prompt pour nommer ou renommer une catégorie.

    Args:
        entities: Liste des entités principales de la catégorie
        keywords: Mots-clés caractérisant la catégorie
        current_name: Nom actuel (si renommage)

    Returns:
        Prompt formaté pour le LLM
    """
    entities_text = ", ".join(entities[:10])
    keywords_text = ", ".join(keywords)

    base_prompt = f"""Tu es un expert en taxonomie et organisation de connaissances.

Voici des informations sur une catégorie de notes :
- Entités principales : {entities_text}
- Mots-clés : {keywords_text}
"""

    if current_name:
        base_prompt += f"\n- Nom actuel : {current_name}\n"

    base_prompt += """
Ta tâche : Propose un nom court, clair et descriptif pour cette catégorie.

Critères pour un bon nom :
- 2-4 mots maximum
- Descriptif et précis
- En français
- Facile à comprendre
- Représentatif du contenu

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{
    "suggested_name": "Nom de la catégorie",
    "alternative_names": ["Alternative 1", "Alternative 2"],
    "reasoning": "Brève explication de ton choix (1 phrase)"
}

JSON :"""

    return base_prompt


def get_category_description_prompt(
    category_name: str,
    entities: List[str],
    keywords: List[str],
    note_count: int
) -> str:
    """
    Génère un prompt pour créer une description détaillée d'une catégorie.

    Args:
        category_name: Nom de la catégorie
        entities: Entités principales de la catégorie
        keywords: Mots-clés de la catégorie
        note_count: Nombre de notes dans la catégorie

    Returns:
        Prompt formaté pour le LLM
    """
    entities_text = ", ".join(entities[:15])
    keywords_text = ", ".join(keywords)

    return f"""Tu es un assistant spécialisé dans la documentation et l'organisation de connaissances.

Voici une catégorie de notes Obsidian :
- Nom : {category_name}
- Entités principales : {entities_text}
- Mots-clés : {keywords_text}
- Nombre de notes : {note_count}

Ta tâche : Rédige une description détaillée et informative de cette catégorie.

La description doit :
- Expliquer clairement le thème et le contenu de la catégorie (2-3 phrases)
- Mentionner les sujets principaux couverts
- Être utile pour quelqu'un qui découvre cette catégorie
- Être en français et bien rédigée

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "description": "Description détaillée de la catégorie",
    "scope": "Étendue du contenu (ex: 'Notes techniques sur le développement Python')",
    "typical_content": "Type de contenu typique (ex: 'Tutoriels, snippets de code, notes de projets')"
}}

JSON :"""


def get_subcategory_suggestion_prompt(
    parent_category_name: str,
    entities: List[str],
    note_count: int,
    keywords: List[str]
) -> str:
    """
    Génère un prompt pour suggérer des sous-catégories.

    Args:
        parent_category_name: Nom de la catégorie parente
        entities: Entités dans la catégorie
        note_count: Nombre de notes
        keywords: Mots-clés

    Returns:
        Prompt formaté pour le LLM
    """
    entities_text = ", ".join(entities[:20])
    keywords_text = ", ".join(keywords)

    return f"""Tu es un expert en organisation hiérarchique de connaissances.

Voici une catégorie qui pourrait bénéficier de sous-catégories :
- Catégorie parente : {parent_category_name}
- Entités ({len(entities)}) : {entities_text}
- Nombre de notes : {note_count}
- Mots-clés : {keywords_text}

Ta tâche : Analyse si cette catégorie devrait être divisée en sous-catégories, et si oui, propose-les.

Critères pour suggérer des sous-catégories :
- La catégorie couvre plusieurs thèmes distincts
- Le nombre de notes est élevé (>15)
- Les entités peuvent être naturellement regroupées

Réponds UNIQUEMENT avec un objet JSON dans ce format exact :
{{
    "should_split": true,
    "reasoning": "Pourquoi diviser cette catégorie",
    "subcategories": [
        {{
            "name": "Nom de la sous-catégorie",
            "description": "Description",
            "expected_note_count": 10
        }}
    ]
}}

Si aucune division n'est nécessaire, mets "should_split": false et "subcategories": []

JSON :"""
